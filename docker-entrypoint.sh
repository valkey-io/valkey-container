#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
# or first arg is `something.conf`
if [ "${1#-}" != "$1" ] || [ "${1%.conf}" != "$1" ]; then
	set -- valkey-server "$@"
fi

# allow the container to be started with `--user`
if [ "$1" = 'valkey-server' ]; then
    if [ "$(id -u)" = '0' ]; then
        find . \! -user valkey -exec chown valkey '{}' +
        exec setpriv --reuid=valkey --regid=valkey --clear-groups -- "$0" "$@"
    else
        if [ ! -w . ]; then
            echo >&2 "error: directory is not writable by current user ($(id -u))"
            echo >&2 "  Check mount permissions or run as root to allow chown"
            exit 1
        fi
    fi
fi


# set an appropriate umask (if one isn't set already)
um="$(umask)"
if [ "$um" = '0022' ]; then
	umask 0077
fi

exec "$@" $VALKEY_EXTRA_FLAGS
