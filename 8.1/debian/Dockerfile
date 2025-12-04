#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "apply-templates.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM debian:trixie-slim AS base

FROM base AS build

ENV VALKEY_DOWNLOAD_SHA 2d47a6afaec7a5383813579c2367193053ec885bc135e810284fe94ccdd324d2

ADD "https://github.com/valkey-io/valkey/archive/refs/tags/8.1.5.tar.gz" /valkey.tar.gz

RUN set -eux; \
	\
	apt-get update; \
	apt-get install -y --no-install-recommends \
		dpkg-dev \
		gcc \
		libc6-dev \
		libssl-dev \
		libsystemd-dev \
		make \
	; \
	rm -rf /var/lib/apt/lists/*; \
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
	echo "Version 8.1.5 is 8.1 or higher - enabling USE_FAST_FLOAT"; \
			apt-get update; \
		apt-get install -y --no-install-recommends g++; \
		rm -rf /var/lib/apt/lists/*; \
		export BUILD_TLS=yes USE_FAST_FLOAT=yes; \
	export USE_SYSTEMD=yes; \
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
	echo '{"spdxVersion":"SPDX-2.3","SPDXID":"SPDXRef-DOCUMENT","name":"valkey-server-sbom","packages":[{"name":"valkey-server","versionInfo":"8.1.5","SPDXID":"SPDXRef-Package--valkey-server","externalRefs":[{"referenceCategory":"PACKAGE-MANAGER","referenceType":"purl","referenceLocator":"pkg:generic/valkey-server@8.1.5?os_name=debian&os_version=trixie"}],"licenseDeclared":"BSD-3-Clause"}]}' > /usr/local/valkey.spdx.json

FROM base

ENV VALKEY_VERSION 8.1.5

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN set -eux; \
	groupadd -r -g 999 valkey; \
	useradd -r -g valkey -u 999 valkey

# runtime dependencies
RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
# add tzdata explicitly for https://github.com/docker-library/redis/issues/138 (see also https://bugs.debian.org/837060 and related)
		tzdata \
		libssl3t64 \
	; \
	rm -rf /var/lib/apt/lists/*

# Install valkey built earlier
COPY --from=build /usr/local /usr/local
RUN mkdir /data && \
	chown valkey:valkey /data && \
	mkdir -p /run/valkey && \
	chown valkey:valkey /run/valkey && \
	valkey-cli --version && \
	valkey-server --version
WORKDIR /data

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 6379
CMD ["valkey-server"]
