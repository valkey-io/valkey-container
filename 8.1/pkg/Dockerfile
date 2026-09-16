#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "apply-templates.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM debian:trixie-slim AS base

FROM base AS fetch

ENV VALKEY_DEB_SUITE debian13
ENV VALKEY_DEB_REPO https://download.valkey.io/packaging/valkey-8.1

RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		ca-certificates \
		curl \
		gnupg \
	; \
	rm -rf /var/lib/apt/lists/*; \
	\
	arch="$(dpkg --print-architecture)"; \
	base="$VALKEY_DEB_REPO/deb/$VALKEY_DEB_SUITE/$arch"; \
	\
# .deb files are not individually signed, so trust comes from the repository
# index: the signed InRelease vouches for Packages, and Packages vouches for
# each .deb.
	export GNUPGHOME="$(mktemp -d)"; \
	curl -fsSL 'https://download.valkey.io/packaging/GPG-KEY-valkey.asc' -o valkey-packaging-key.asc; \
	gpg --batch --import valkey-packaging-key.asc; \
	rm -f valkey-packaging-key.asc; \
# pin the signing key to its known fingerprint: download.valkey.io serves
# both the key and the index/packages it vouches for, so an unpinned import
# trusts whatever key that origin happens to hand back. this key expires
# 2029-04-15; when the build starts failing here, fetch and verify Valkey's
# replacement key out of band and update the fingerprint below
	gpg --batch --list-keys --with-colons \
		| awk -F: '$1 == "fpr" { print $10 }' \
		| grep -qx '8A7E329444EBA7A083C8B884568774152429690D'; \
	\
	curl -fsSL "$base/InRelease" -o InRelease; \
	gpg --batch --verify InRelease; \
	gpg --batch --output Release.txt --decrypt InRelease; \
	\
	curl -fsSL "$base/Packages" -o Packages; \
	awk '/^SHA256:/ { f = 1; next } /^[^ ]/ { f = 0 } f && $3 == "Packages" { print $1 "  Packages" }' Release.txt \
		| sha256sum -c -; \
	\
	mkdir -p /debs; \
	for pkg in valkey-server valkey-tools valkey-sentinel valkey-compat-redis; do \
		filename="$(awk -v pkg="$pkg" '$1 == "Package:" { cur = $2 } cur == pkg && $1 == "Filename:" { print $2; exit }' Packages)"; \
		sha256="$(awk -v pkg="$pkg" '$1 == "Package:" { cur = $2 } cur == pkg && $1 == "SHA256:" { print $2; exit }' Packages)"; \
		[ -n "$filename" ] || { echo >&2 "error: no Filename found for package '$pkg' in $base/Packages"; exit 1; }; \
		[ -n "$sha256" ] || { echo >&2 "error: no SHA256 found for package '$pkg' in $base/Packages"; exit 1; }; \
		curl -fsSL "$base/${filename#./}" -o "/debs/$pkg.deb"; \
		echo "$sha256  /debs/$pkg.deb" | sha256sum -c -; \
		if [ "$pkg" = 'valkey-server' ]; then \
			echo "$base/${filename#./}" > /debs/download-url; \
		fi; \
	done; \
	\
	rm -rf "$GNUPGHOME" InRelease Release.txt Packages

FROM base

ENV VALKEY_VERSION 8.1.10
# protected-mode is off by default via ENV, not CMD: a derived image can
# (and some of the shared tests do) replace CMD entirely, but ENV values
# set here are inherited by anything built FROM this image, and
# docker-entrypoint.sh appends $VALKEY_EXTRA_FLAGS after whatever
# CMD/args it is given, so protected mode still ends up disabled
# on every invocation path, including ones that supply their own CMD
ENV VALKEY_EXTRA_FLAGS --protected-mode no

LABEL org.opencontainers.image.source="https://github.com/valkey-io/valkey"

# add our user and group first to make sure their IDs get assigned consistently;
# creating them before installing means the package's postinst adopts these
# instead of allocating a dynamic system uid
RUN set -eux; \
	groupadd -r -g 999 valkey; \
	useradd -r -g valkey -u 999 valkey

COPY --from=fetch /debs /tmp/debs

RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		/tmp/debs/valkey-server.deb \
		/tmp/debs/valkey-tools.deb \
		/tmp/debs/valkey-sentinel.deb \
		/tmp/debs/valkey-compat-redis.deb \
# add tzdata explicitly for https://github.com/docker-library/redis/issues/138 (see also https://bugs.debian.org/837060 and related)
		tzdata \
		# add tini to act as PID 1 and reap orphaned/zombie processes
		tini \
	; \
	rm -rf /var/lib/apt/lists/*; \
	\
# the installed package must be the version this image claims to be
	dpkg-query --showformat '${Version}' --show valkey-server | grep -E "^$VALKEY_VERSION-"; \
	\
# drop packaging that assumes a systemd/sysvinit host; this image runs
# valkey-server directly with no config file, exactly like the source-built variants
	rm -rf \
		/etc/default/valkey-server \
		/etc/init.d/valkey-server \
		/etc/logrotate.d/valkey-server \
		/etc/logrotate.d/valkey-sentinel \
		/etc/valkey/valkey.conf \
		/etc/valkey/sentinel.conf \
		/lib/systemd/system/valkey-server.service \
		/lib/systemd/system/valkey-server@.service \
		/lib/systemd/system/valkey-sentinel.service \
		/lib/systemd/system/valkey-sentinel@.service \
		/var/lib/valkey \
		/var/log/valkey \
	; \
	\
	SPDX_CREATED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
	SPDX_UUID="$(cat /proc/sys/kernel/random/uuid)"; \
	SPDX_DOWNLOAD="$(cat /tmp/debs/download-url)"; \
	echo '{"spdxVersion":"SPDX-2.3","dataLicense":"CC0-1.0","SPDXID":"SPDXRef-DOCUMENT","name":"valkey-server-sbom","documentNamespace":"https://valkey.io/spdxdocs/valkey-server-sbom-8.1.10-debian-trixie-@SPDX_UUID@","creationInfo":{"created":"@SPDX_CREATED@","creators":["Organization: The Valkey Project","Tool: valkey-container"]},"packages":[{"name":"valkey-server","versionInfo":"8.1.10","SPDXID":"SPDXRef-Package--valkey-server","supplier":"Organization: The Valkey Project","downloadLocation":"@SPDX_DOWNLOAD@","filesAnalyzed":false,"externalRefs":[{"referenceCategory":"PACKAGE-MANAGER","referenceType":"purl","referenceLocator":"pkg:generic/valkey-server@8.1.10?os_name=debian&os_version=trixie"},{"referenceCategory":"SECURITY","referenceType":"cpe23Type","referenceLocator":"cpe:2.3:a:lfprojects:valkey:8.1.10:*:*:*:*:*:*:*"}],"licenseDeclared":"BSD-3-Clause"}],"relationships":[{"spdxElementId":"SPDXRef-DOCUMENT","relationshipType":"DESCRIBES","relatedSpdxElement":"SPDXRef-Package--valkey-server"}]}' \
		| sed \
			-e "s|@SPDX_CREATED@|$SPDX_CREATED|g" \
			-e "s|@SPDX_UUID@|$SPDX_UUID|g" \
			-e "s|@SPDX_DOWNLOAD@|$SPDX_DOWNLOAD|g" \
		> /usr/local/valkey.spdx.json; \
	\
	rm -rf /tmp/debs; \
	\
	valkey-cli --version; \
	valkey-server --version

RUN mkdir /data && \
	chown valkey:valkey /data && \
	chmod 1777 /data && \
	mkdir -p /run/valkey && \
	chown valkey:valkey /run/valkey && \
	chmod 1777 /run/valkey
WORKDIR /data

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["tini", "--", "docker-entrypoint.sh"]

EXPOSE 6379
CMD ["valkey-server"]
