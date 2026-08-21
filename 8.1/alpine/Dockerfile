#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "apply-templates.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM alpine:3.24 AS base

FROM base AS build

ENV VALKEY_DOWNLOAD_SHA c74e50cd83f6d398a3dc570e04ac2fe538249585d021f76ee2449bbf9ebd04ed

ADD "https://github.com/valkey-io/valkey/archive/refs/tags/8.1.10.tar.gz" /valkey.tar.gz

RUN set -eux; \
	\
	apk add --no-cache \
		coreutils \
		dpkg-dev dpkg \
		gcc \
		g++ \
		linux-headers \
		make \
		musl-dev \
		openssl-dev \
		git \
		autoconf \
		automake \
		libtool \
	; \
# build libbacktrace from source (not available as Alpine package)
# pinned to commit 96664e69b1ecdb76e824be1d9e8f475b76dd08cf (2026-05-03)
	git clone https://github.com/ianlancetaylor/libbacktrace.git /tmp/libbacktrace; \
	cd /tmp/libbacktrace; \
	git reset --hard 96664e69b1ecdb76e824be1d9e8f475b76dd08cf; \
	./configure --prefix=/usr; \
	make -j "$(nproc)"; \
	make install; \
	cd /; \
	rm -rf /tmp/libbacktrace; \
	\
			echo "$VALKEY_DOWNLOAD_SHA *valkey.tar.gz" | sha256sum -c -; \
		\
	mkdir -p /usr/src/valkey; \
	tar -xzf valkey.tar.gz -C /usr/src/valkey --strip-components=1; \
	rm valkey.tar.gz; \
	\
# disable Valkey protected mode [1] as it is unnecessary in context of Docker
# (ports are not automatically exposed when running inside Docker, but rather explicitly by specifying -p / -P)
	grep -E '^ *createBoolConfig[(]"protected-mode",.*, *1 *,.*[)],$' /usr/src/valkey/src/config.c; \
	sed -ri 's!^( *createBoolConfig[(]"protected-mode",.*, *)1( *,.*[)],)$!\10\2!' /usr/src/valkey/src/config.c; \
	grep -E '^ *createBoolConfig[(]"protected-mode",.*, *0 *,.*[)],$' /usr/src/valkey/src/config.c; \
# for future reference, we modify this directly in the source instead of just supplying a default configuration flag because apparently "if you specify any argument to valkey-server, [it assumes] you are going to specify everything"
# (more exactly, this makes sure the default behavior of "save on SIGTERM" stays functional by default)
	\
# https://github.com/jemalloc/jemalloc/issues/467 -- we need to patch the "./configure" for the bundled jemalloc to match how Debian compiles, for compatibility
# (also, we do cross-builds, so we need to embed the appropriate "--build=xxx" values to that "./configure" invocation)
	gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)"; \
	extraJemallocConfigureFlags="--build=$gnuArch"; \
# https://salsa.debian.org/debian/jemalloc/-/blob/c0a88c37a551be7d12e4863435365c9a6a51525f/debian/rules#L8-23
	dpkgArch="$(dpkg --print-architecture)"; \
	case "${dpkgArch##*-}" in \
		amd64 | i386 | x32) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=12" ;; \
		*) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=16" ;; \
	esac; \
	extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-hugepage=21"; \
	grep -F 'cd jemalloc && ./configure ' /usr/src/valkey/deps/Makefile; \
	sed -ri 's!cd jemalloc && ./configure !&'"$extraJemallocConfigureFlags"' !' /usr/src/valkey/deps/Makefile; \
	grep -F "cd jemalloc && ./configure $extraJemallocConfigureFlags " /usr/src/valkey/deps/Makefile; \
	\
	echo "Version 8.1.10 is 8.1 or higher - enabling USE_FAST_FLOAT"; \
			export BUILD_TLS=yes USE_FAST_FLOAT=yes; \
	export USE_LIBBACKTRACE=yes; \
	make -C /usr/src/valkey -j "$(nproc)" all; \
	make -C /usr/src/valkey install; \
	\
	serverMd5="$(md5sum /usr/local/bin/valkey-server | cut -d' ' -f1)"; export serverMd5; \
	find /usr/local/bin/valkey* -maxdepth 0 \
		-type f -not -name valkey-server \
		-exec sh -eux -c ' \
			md5="$(md5sum "$1" | cut -d" " -f1)"; \
			test "$md5" = "$serverMd5"; \
		' -- '{}' ';' \
		-exec ln -svfT 'valkey-server' '{}' ';' \
	; \
	\
	SPDX_CREATED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
	SPDX_UUID="$(cat /proc/sys/kernel/random/uuid)"; \
	echo '{"spdxVersion":"SPDX-2.3","dataLicense":"CC0-1.0","SPDXID":"SPDXRef-DOCUMENT","name":"valkey-server-sbom","documentNamespace":"https://valkey.io/spdxdocs/valkey-server-sbom-8.1.10-alpine-3.24-@SPDX_UUID@","creationInfo":{"created":"@SPDX_CREATED@","creators":["Organization: The Valkey Project","Tool: valkey-container"]},"packages":[{"name":"valkey-server","versionInfo":"8.1.10","SPDXID":"SPDXRef-Package--valkey-server","supplier":"Organization: The Valkey Project","downloadLocation":"https://github.com/valkey-io/valkey/archive/refs/tags/8.1.10.tar.gz","filesAnalyzed":false,"externalRefs":[{"referenceCategory":"PACKAGE-MANAGER","referenceType":"purl","referenceLocator":"pkg:generic/valkey-server@8.1.10?os_name=alpine&os_version=3.24"},{"referenceCategory":"SECURITY","referenceType":"cpe23Type","referenceLocator":"cpe:2.3:a:lfprojects:valkey:8.1.10:*:*:*:*:*:*:*"}],"licenseDeclared":"BSD-3-Clause"}],"relationships":[{"spdxElementId":"SPDXRef-DOCUMENT","relationshipType":"DESCRIBES","relatedSpdxElement":"SPDXRef-Package--valkey-server"}]}' \
		| sed -e "s|@SPDX_CREATED@|$SPDX_CREATED|g" -e "s|@SPDX_UUID@|$SPDX_UUID|g" > /usr/local/valkey.spdx.json

FROM base

ENV VALKEY_VERSION 8.1.10

LABEL org.opencontainers.image.source="https://github.com/valkey-io/valkey"

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN set -eux; \
# alpine already has a gid 999, so we'll use the next id
	addgroup -S -g 1000 valkey; \
	adduser -S -G valkey -u 999 valkey

# runtime dependencies
RUN set -eux; \
	apk add --no-cache \
# add tzdata for https://github.com/docker-library/redis/issues/138
		tzdata \
		# add setpriv for step down from root.
		setpriv \
		openssl \
		libgcc \
		# add tini to act as PID 1 and reap orphaned/zombie processes
		tini \
	;

# Install valkey built earlier
COPY --from=build /usr/local /usr/local
RUN mkdir /data && \
	chown valkey:valkey /data && \
	chmod 1777 /data && \
	mkdir -p /run/valkey && \
	chown valkey:valkey /run/valkey && \
	chmod 1777 /run/valkey && \
	valkey-cli --version && \
	valkey-server --version
WORKDIR /data

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["tini", "--", "docker-entrypoint.sh"]

EXPOSE 6379
CMD ["valkey-server"]
