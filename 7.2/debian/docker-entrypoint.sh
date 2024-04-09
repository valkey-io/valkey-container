#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
# or first arg is `something.conf`
if [ "${1#-}" != "$1" ] || [ "${1%.conf}" != "$1" ]; then
	set -- valkey-server "$@"
fi

# allow the container to be started with `--user`
if [ "$1" = 'valkey-server' -a "$(id -u)" = '0' ]; then
	find . \! -user valkey -exec chown valkey '{}' +
	exec gosu valkey "$0" "$@"
fi

# set an appropriate umask (if one isn't set already)
um="$(umask)"
if [ "$um" = '0022' ]; then
	umask 0077
fi

exec "$@"
