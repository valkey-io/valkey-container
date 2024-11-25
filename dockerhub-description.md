# Quick reference

-	**Maintained by**:
	[the Valkey Community](https://github.com/valkey-io/valkey-container)

-	**Where to get help**:
	Please open an Issue stating your question on [the Valkey Community](https://github.com/valkey-io/valkey-container/issues).

# Supported tags and respective `Dockerfile` links
- [`unstable`, `unstable-bookworm`](https://github.com/valkey-io/valkey-container/blob/master/unstable/debian/Dockerfile)
- [`unstable-alpine`, `unstable-alpine3.20`](https://github.com/valkey-io/valkey-container/blob/master/unstable/alpine/Dockerfile)
- [`8.0.1`, `8.0`, `8`, `latest`, `8.0.1-bookworm`, `8.0-bookworm`, `8-bookworm`, `bookworm`](https://github.com/valkey-io/valkey-container/blob/master/8.0/debian/Dockerfile)
- [`8.0.1-alpine`, `8.0-alpine`, `8-alpine`, `alpine`, `8.0.1-alpine3.20`, `8.0-alpine3.20`, `8-alpine3.20`, `alpine3.20`](https://github.com/valkey-io/valkey-container/blob/master/8.0/alpine/Dockerfile)
- [`7.2.7`, `7.2`, `7`, `7.2.7-bookworm`, `7.2-bookworm`, `7-bookworm`](https://github.com/valkey-io/valkey-container/blob/master/7.2/debian/Dockerfile)
- [`7.2.7-alpine`, `7.2-alpine`, `7-alpine`, `7.2.7-alpine3.20`, `7.2-alpine3.20`, `7-alpine3.20`](https://github.com/valkey-io/valkey-container/blob/master/7.2/alpine/Dockerfile)

What is [Valkey](https://github.com/valkey-io/valkey)?
--------------
Valkey is a high-performance data structure server that primarily serves key/value workloads.
It supports a wide range of native structures and an extensible plugin system for adding new data structures and access patterns.

# Security

For the ease of accessing Valkey from other containers via Docker networking, the "Protected mode" is turned off by default. This means that if you expose the port outside of your host (e.g., via `-p` on `docker run`), it will be open without a password to anyone. It is **highly** recommended to set a password (by supplying a config file) if you plan on exposing your Valkey instance to the internet. For further information, see the following links about Valkey security:

-	[Valkey documentation on security](https://valkey.io/topics/security/)
-	[Protected mode](https://valkey.io/topics/security/#protected-mode)
-	[A few things about security by antirez](http://antirez.com/news/96)

# How to use this image

## Start a valkey instance

```console
$ docker run --name some-valkey -d valkey/valkey
```

## Start with persistent storage

```console
$ docker run --name some-valkey -d valkey/valkey valkey-server --save 60 1 --loglevel warning
```

There are several different persistence strategies to choose from. This one will save a snapshot of the DB every 60 seconds if at least 1 write operation was performed (it will also lead to more logs, so the `loglevel` option may be desirable). If persistence is enabled, data is stored in the `VOLUME /data`, which can be used with `--volumes-from some-volume-container` or `-v /docker/host/dir:/data` (see [docs.docker volumes](https://docs.docker.com/engine/tutorials/dockervolumes/)).

## Connecting via `valkey-cli`

```console
$ docker run -it --network some-network --rm valkey/valkey valkey-cli -h some-valkey
```

## Pass additional start arguments with environment variable

In case you'd like to configure the start arguments of `valkey-server`
with environment variable, you can pass them with `VALKEY_EXTRA_FLAGS`
without having to overwrite the CMD:
```console
$ docker run --env VALKEY_EXTRA_FLAGS='--save 60 1 --loglevel warning' valkey/valkey
```

## Additionally, If you want to use your own valkey.conf ...

You can create your own Dockerfile that adds a valkey.conf from the context into /data/, like so.

```dockerfile
FROM valkey/valkey
COPY valkey.conf /usr/local/etc/valkey/valkey.conf
CMD [ "valkey-server", "/usr/local/etc/valkey/valkey.conf" ]
```

Alternatively, you can specify something along the same lines with `docker run` options.

```console
$ docker run -v /myvalkey/conf:/usr/local/etc/valkey --name myvalkey valkey/valkey valkey-server /usr/local/etc/valkey/valkey.conf
```

Where `/myvalkey/conf/` is a local directory containing your `valkey.conf` file. Using this method means that there is no need for you to have a Dockerfile for your valkey container.

The mapped directory should be writable, as depending on the configuration and mode of operation, Valkey may need to create additional configuration files or rewrite existing ones.

# Image Variants

The `valkey` images come in many flavors, each designed for a specific use case.

## `valkey/valkey:<version>`

This is the defacto image. If you are unsure about what your needs are, you probably want to use this one. It is designed to be used both as a throw away container (mount your source code and start the container to start your app), as well as the base to build other images off of.

Some of these tags may have names like bookworm in them. These are the suite code names for releases of [Debian](https://wiki.debian.org/DebianReleases) and indicate which release the image is based on. If your image needs to install any additional packages beyond what comes with the image, you'll likely want to specify one of these explicitly to minimize breakage when there are new releases of Debian.

## `valkey/valkey:<version>-alpine`

This image is based on the popular [Alpine Linux project](https://alpinelinux.org), available in [the `alpine` official image](https://hub.docker.com/_/alpine). Alpine Linux is much smaller than most distribution base images (~5MB), and thus leads to much slimmer images in general.

This variant is useful when final image size being as small as possible is your primary concern. The main caveat to note is that it does use [musl libc](https://musl.libc.org) instead of [glibc and friends](https://www.etalabs.net/compare_libcs.html), so software will often run into issues depending on the depth of their libc requirements/assumptions. See [this Hacker News comment thread](https://news.ycombinator.com/item?id=10782897) for more discussion of the issues that might arise and some pro/con comparisons of using Alpine-based images.

To minimize image size, it's uncommon for additional related tools (such as `git` or `bash`) to be included in Alpine-based images. Using this image as a base, add the things you need in your own Dockerfile (see the [`alpine` image description](https://hub.docker.com/_/alpine/) for examples of how to install packages if you are unfamiliar).

# License

View [license information](https://github.com/valkey-io/valkey/blob/unstable/COPYING) for the software contained in this image.

As with all Docker images, these likely also contain other software which may be under other licenses (such as Bash, etc from the base distribution, along with any direct or indirect dependencies of the primary software being contained).

As for any pre-built image usage, it is the image user's responsibility to ensure that any use of this image complies with any relevant licenses for all software contained within.
