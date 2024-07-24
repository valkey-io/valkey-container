#!/bin/bash
set -eo pipefail

dir="$(dirname "$(readlink -f "$BASH_SOURCE")")"

image="$1"

cname="valkey-container-$RANDOM-$RANDOM"
cid="$(docker run -d --name "$cname" "$image")"
trap "docker rm -vf $cid > /dev/null" EXIT

valkey-cli() {
	docker run --rm -i \
		--link "$cname":valkey \
		--entrypoint valkey-cli \
		"$image" \
		-h valkey \
		"$@"
}

. "$dir/../../retry.sh" --tries 20 '[ "$(valkey-cli ping)" = "PONG" ]'

[ "$(valkey-cli set mykey somevalue)" = 'OK' ]
[ "$(valkey-cli get mykey)" = 'somevalue' ]

docker stop "$cname"
docker start "$cname"

. "$dir/../../retry.sh" --tries 20 '[ "$(valkey-cli ping)" = "PONG" ]'

[ "$(valkey-cli get mykey)" = 'somevalue' ]