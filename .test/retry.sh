#!/usr/bin/env bash
set -e

opts="$(getopt -o 'i:c:t:s:' --long 'image:,cid:,tries:,sleep:' -- "$@")"
eval set -- "$opts"
while true; do
  case "$1" in
  -i | --image)
    image="$2"
    shift 2
    ;;
  -c | --cid)
    cid="$2"
    shift 2
    ;;
  -t | --tries)
    tries="$2"
    shift 2
    ;;
  -s | --sleep)
    sleep="$2"
    shift 2
    ;;
  --)
    shift
    break
    ;;
  esac
done

if [ $# -eq 0 ]; then
  echo >&2 'retry.sh requires a command to run'
  exit 1
fi

: "${tries:=10}"
: "${sleep:=2}"

while ! eval "$@" &>/dev/null; do
  ((tries--))
  if [ $tries -le 0 ]; then
    echo >&2 "${image:-the container} failed to accept connections in a reasonable amount of time!"
    [ "$cid" ] && (set -x && docker logs "$cid") >&2
    (set -x && eval "$@") >&2
    exit 1
  fi
  if [ "$cid" ] && [ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null)" != 'true' ]; then
    echo >&2 "${image:-the container} stopped unexpectedly!"
    (set -x && docker logs "$cid") >&2
    exit 1
  fi
  echo -n . >&2
  sleep "$sleep"
done
