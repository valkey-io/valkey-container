#!/usr/bin/env bash
set -eo pipefail

dir="$(dirname "$(readlink -f "$BASH_SOURCE")")"

image="$1"

# Build a test image that runs as non-root with a read-only /data
testImage="$("$dir/../image-name.sh" librarytest/valkey-readonly-data "$image")"
"$dir/../docker-build.sh" "$dir" "$testImage" <<-EOD
	FROM $image
	RUN chmod 555 /data
	USER valkey
	CMD ["valkey-server", "--save", "", "--appendonly", "no"]
EOD

network="valkey-network-$RANDOM-$RANDOM"
docker network create "$network" >/dev/null

cname="valkey-container-$RANDOM-$RANDOM"
cid="$(docker run -d --name "$cname" --network "$network" "$testImage")"

trap "docker rm -vf '$cid' >/dev/null; docker network rm '$network' >/dev/null" EXIT

# Verify the container starts and responds despite /data being read-only
valkey-cli() {
	docker run --rm -i \
		--network "$network" \
		--entrypoint valkey-cli \
		"$image" \
		-h "$cname" \
		"$@"
}

. "$dir/../../retry.sh" --tries 20 '[ "$(valkey-cli ping)" = "PONG" ]'

# Verify the warning was emitted
logs="$(docker logs "$cid" 2>&1)"
if ! echo "$logs" | grep -q "warning: directory"; then
	echo >&2 "ERROR: expected writable warning in logs but did not find it"
	exit 1
fi

echo "PASS: container started with read-only /data and emitted warning"
