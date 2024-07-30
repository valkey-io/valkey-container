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

[ "$(valkey-cli set mykey somevalue)" = "OK" ]
[ "$(valkey-cli get mykey)" = "somevalue" ]

docker stop "$cname" >/dev/null
docker start "$cname" >/dev/null

. "$dir/../../retry.sh" --tries 20 '[ "$(valkey-cli ping)" = "PONG" ]'

[ "$(valkey-cli get mykey)" = "somevalue" ]
