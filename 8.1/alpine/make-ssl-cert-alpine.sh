#!/bin/sh
set -e

if [ $# -ne 2 ]; then
  echo "Usage: make-ssl-cert <cert_file> <key_file>" >&2
  exit 1
fi

mkdir -p "$(dirname "$1")" "$(dirname "$2")"
openssl req -new -x509 -days 3650 -nodes -out "$1" -keyout "$2" -subj "/CN=localhost"
