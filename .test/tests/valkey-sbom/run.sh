#!/usr/bin/env bash
set -eo pipefail

dir="$(dirname "$(readlink -f "$BASH_SOURCE")")"

image="$1"

# Mirror of the official python image (avoids Docker Hub pull limits)
pythonImage='public.ecr.aws/docker/library/python:3.12-slim'

# Pre-pull with retries: parallel CI jobs pulling the same image from shared
# runner IPs can hit anonymous registry rate limits (toomanyrequests).
# NOTE: retry.sh is sourced and its --image flag would clobber our $image.
. "$dir/../../retry.sh" --tries 10 --sleep 15 "docker pull -q '$pythonImage'"

# Extract the SBOM shipped in the image
sbom="$(docker run --rm --entrypoint cat "$image" /usr/local/valkey.spdx.json)"

# Validate it with the reference SPDX validator (spdx-tools).
# Runs in a throwaway container so the test host only needs docker.
# pyspdxtools detects the document format from the file extension, hence the
# .spdx.json filename. Version pinned for reproducible CI runs.
if ! echo "$sbom" | docker run --rm -i "$pythonImage" sh -euc '
	pip install --quiet --no-input "spdx-tools==0.8.3" >/dev/null 2>&1
	cat > /tmp/sbom.spdx.json
	pyspdxtools -i /tmp/sbom.spdx.json
'; then
	echo >&2 "ERROR: /usr/local/valkey.spdx.json is not a valid SPDX 2.3 document:"
	echo >&2 "$sbom"
	exit 1
fi

echo "PASS: SBOM is a valid SPDX 2.3 document"
