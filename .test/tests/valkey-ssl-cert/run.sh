#!/usr/bin/env bash
set -eo pipefail

dir="$(dirname "$(readlink -f "$BASH_SOURCE")")"
testDir="$(readlink -f "$(dirname "$BASH_SOURCE")")"
testName="$(basename "$testDir")"

image="$1"

# Determine if this is Alpine or Debian variant
imageVariant="$(docker run --rm --entrypoint sh "$image" -c 'if [ -f /etc/alpine-release ]; then echo alpine; else echo debian; fi')"

network="valkey-network-$RANDOM-$RANDOM"
docker network create "$network" >/dev/null

cname="valkey-container-$RANDOM-$RANDOM"
cid="$(docker run -d --name "$cname" --network "$network" "$image")"

trap "docker rm -vf '$cid' >/dev/null; docker network rm '$network' >/dev/null" EXIT

# Test OpenSSL is available
echo "Testing OpenSSL availability..."
docker exec "$cid" openssl version >/dev/null
echo "✓ OpenSSL is accessible"

# Test make-ssl-cert functionality
if [ "$imageVariant" = "alpine" ]; then
    echo "Testing Alpine make-ssl-cert..."
    
    # Test basic certificate generation
    docker exec "$cid" make-ssl-cert /tmp/test.pem /tmp/test.key
    
    # Verify files exist
    docker exec "$cid" test -f /tmp/test.pem
    docker exec "$cid" test -f /tmp/test.key
    
    # Test nested directory creation
    docker exec "$cid" make-ssl-cert /deep/nested/cert.pem /another/path/key.pem
    docker exec "$cid" test -f /deep/nested/cert.pem
    docker exec "$cid" test -f /another/path/key.pem
    
    # Test error handling
    if docker exec "$cid" make-ssl-cert 2>/dev/null; then
        echo "ERROR: Should have failed with no arguments"
        exit 1
    fi
    
    if docker exec "$cid" make-ssl-cert /tmp/only-one 2>/dev/null; then
        echo "ERROR: Should have failed with one argument"
        exit 1
    fi
    
else
    echo "Testing Debian make-ssl-cert..."
    
    # Test standard generation
    docker exec "$cid" env DEBIAN_FRONTEND=noninteractive make-ssl-cert generate-default-snakeoil
    
    # Verify files exist
    docker exec "$cid" test -f /etc/ssl/certs/ssl-cert-snakeoil.pem
    docker exec "$cid" test -f /etc/ssl/private/ssl-cert-snakeoil.key
fi

# Common tests for both variants
echo "Testing certificate validity..."

if [ "$imageVariant" = "alpine" ]; then
    certFile="/tmp/test.pem"
    keyFile="/tmp/test.key"
else
    certFile="/etc/ssl/certs/ssl-cert-snakeoil.pem"
    keyFile="/etc/ssl/private/ssl-cert-snakeoil.key"
fi

# Verify certificate is valid X.509
docker exec "$cid" openssl x509 -in "$certFile" -noout -text >/dev/null

# Verify private key is valid
docker exec "$cid" openssl rsa -in "$keyFile" -check -noout >/dev/null 2>&1

# Verify certificate subject
subject="$(docker exec "$cid" openssl x509 -in "$certFile" -noout -subject)"
if [ "$imageVariant" = "alpine" ]; then
    if [[ "$subject" != *"CN=localhost"* ]] && [[ "$subject" != *"CN = localhost"* ]]; then
        echo "ERROR: Certificate subject should contain CN=localhost, got: $subject"
        exit 1
    fi
else
    # For Debian, just verify it has some CN field
    if [[ "$subject" != *"CN="* ]] && [[ "$subject" != *"CN ="* ]]; then
        echo "ERROR: Certificate subject should contain CN field, got: $subject"
        exit 1
    fi
fi

# Verify certificate and key match
certMod="$(docker exec "$cid" openssl x509 -noout -modulus -in "$certFile" | openssl md5)"
keyMod="$(docker exec "$cid" sh -c "openssl rsa -noout -modulus -in '$keyFile' 2>/dev/null | openssl md5")"

if [ "$certMod" != "$keyMod" ]; then
    echo "ERROR: Certificate and key modulus don't match"
    exit 1
fi

# Edge case tests
echo "Testing edge cases..."

if [ "$imageVariant" = "alpine" ]; then
    # Test with special characters in filenames
    docker exec "$cid" make-ssl-cert "/tmp/cert with spaces.pem" "/tmp/key-with-dashes.pem"
    docker exec "$cid" test -f "/tmp/cert with spaces.pem"
    docker exec "$cid" test -f "/tmp/key-with-dashes.pem"
    
    # Test overwriting existing files
    firstSerial="$(docker exec "$cid" openssl x509 -in "$certFile" -noout -serial)"
    docker exec "$cid" make-ssl-cert "$certFile" "$keyFile"
    secondSerial="$(docker exec "$cid" openssl x509 -in "$certFile" -noout -serial)"
    
    if [ "$firstSerial" = "$secondSerial" ]; then
        echo "ERROR: Certificate should have been overwritten"
        exit 1
    fi
else
    # Test self-signed certificate validates
    if ! docker exec "$cid" openssl verify -CAfile "$certFile" "$certFile" 2>/dev/null | grep -q "OK"; then
        echo "ERROR: Self-signed certificate should validate"
        exit 1
    fi
    
    # Test key size is reasonable (should be 2048 bits)
    keySize="$(docker exec "$cid" openssl rsa -in "$keyFile" -text -noout 2>/dev/null | grep "Private-Key" | grep -o "[0-9]*" | head -1)"
    if [ "$keySize" -lt 2048 ]; then
        echo "ERROR: Key size should be at least 2048 bits, got $keySize"
        exit 1
    fi
fi

# Test certificate validity period (should be ~10 years)
notAfter="$(docker exec "$cid" openssl x509 -in "$certFile" -noout -enddate | cut -d= -f2)"
currentYear="$(date +%Y)"
certYear="$(date -d "$notAfter" +%Y 2>/dev/null || echo "2035")"
yearDiff=$((certYear - currentYear))

if [ "$yearDiff" -lt 9 ] || [ "$yearDiff" -gt 11 ]; then
    echo "ERROR: Certificate should be valid for ~10 years, got $yearDiff years"
    exit 1
fi

# Test file permissions are secure (Alpine only)
if [ "$imageVariant" = "alpine" ]; then
    keyPerm="$(docker exec "$cid" stat -c %a "$keyFile")"
    if [ "$keyPerm" != "600" ]; then
        echo "ERROR: Private key should have 600 permissions, got $keyPerm"
        exit 1
    fi
fi

echo "✓ All SSL certificate tests (including edge cases) passed for $imageVariant variant"
