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

# Build the reference SPDX validator (spdx-tools) into its own image, so the
# test host only needs docker. Version pinned for reproducible CI runs.
# This is a separate step from validation below so that an install failure
# (PyPI outage, yanked release) is not misreported as an invalid SBOM.
# The tag is fixed rather than derived from $image because the validator does
# not depend on the image under test.
validatorImage='librarytest/valkey-sbom-validator:spdx-tools-0.8.3'
if ! "$dir/../docker-build.sh" "$dir" "$validatorImage" <<-EOD
	FROM $pythonImage
	RUN pip install --no-input "spdx-tools==0.8.3"
EOD
then
	echo >&2 "ERROR: could not build the spdx-tools validator image; this is an"
	echo >&2 "infrastructure failure (registry or PyPI), not an SBOM problem."
	exit 1
fi

# Extract the SBOM shipped in the image
sbom="$(docker run --rm --entrypoint cat "$image" /usr/local/valkey.spdx.json)"

# pyspdxtools infers the document format from the file extension, hence the
# .spdx.json filename.
if ! echo "$sbom" | docker run --rm -i --entrypoint sh "$validatorImage" -euc '
	cat > /tmp/sbom.spdx.json
	pyspdxtools -i /tmp/sbom.spdx.json
'; then
	echo >&2 "ERROR: /usr/local/valkey.spdx.json is not a valid SPDX 2.3 document:"
	echo >&2 "$sbom"
	exit 1
fi

echo "PASS: SBOM is a valid SPDX 2.3 document"
