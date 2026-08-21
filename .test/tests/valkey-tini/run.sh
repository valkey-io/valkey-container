#!/usr/bin/env bash
set -eo pipefail

dir="$(dirname "$(readlink -f "$BASH_SOURCE")")"

image="$1"

network="valkey-network-$RANDOM-$RANDOM"
docker network create "$network" >/dev/null

cname="valkey-container-$RANDOM-$RANDOM"
cid="$(docker run -d --name "$cname" --network "$network" "$image")"

trap "docker rm -vf '$cid' >/dev/null; docker network rm '$network' >/dev/null" EXIT

valkey-cli() {
  docker run --rm -i \
    --network "$network" \
    --entrypoint valkey-cli \
    "$image" \
    -h "$cname" \
    "$@"
}

. "$dir/../../retry.sh" --tries 20 '[ "$(valkey-cli ping)" = "PONG" ]'

# tini must be PID 1 so it can reap orphaned processes (e.g. left behind by exec-based healthchecks/probes)
[ "$(docker exec "$cid" cat /proc/1/comm)" = 'tini' ]

# Simulate an orphaned process: spawn a detached shell whose child outlives it,
# so the child gets reparented to PID 1. Without an init reaping zombies, it
# would remain as a defunct process indefinitely.
docker exec -d "$cid" sh -c 'sleep 2 & exit 0'
sleep 3
[ "$(docker exec "$cid" sh -c "cat /proc/*/stat 2>/dev/null | awk '\$3 == \"Z\"' | wc -l")" = '0' ]
