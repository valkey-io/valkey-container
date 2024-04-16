# Quick reference

-	**Maintained by**:  
	[the Valkey Community](https://github.com/valkey-io/valkey-container)

-	**Where to get help**:  
	Please open an Issue stating your question on [the Valkey Community](https://github.com/valkey-io/valkey-container/issues).

# Supported tags and respective `Dockerfile` links
- [`unstable`, `unstable-bookworm`](https://github.com/valkey-io/valkey-container/blob/master/unstable/debian/Dockerfile)
- [`unstable-alpine`, `unstable-alpine3.19`](https://github.com/valkey-io/valkey-container/blob/master/unstable/alpine/Dockerfile)
- [`7.2`, `7.2-bookworm`, `7.2.5`, `7.2.5-bookworm`](https://github.com/valkey-io/valkey-container/blob/master/7.2/debian/Dockerfile)
- [`7.2-alpine`, `7.2-alpine3.19`, `7.2.5-alpine`, `7.2.5-alpine3.19`](https://github.com/valkey-io/valkey-container/blob/master/7.2/alpine/Dockerfile)

What is [Valkey](https://github.com/valkey-io/valkey)?
--------------
Valkey is a high-performance data structure server that primarily serves key/value workloads.
It supports a wide range of native structures and an extensible plugin system for adding new data structures and access patterns.

# Security

For the ease of accessing Valkey from other containers via Docker networking, the "Protected mode" is turned off by default. This means that if you expose the port outside of your host (e.g., via `-p` on `docker run`), it will be open without a password to anyone. It is **highly** recommended to set a password (by supplying a config file) if you plan on exposing your Valkey instance to the internet. 

# How to use this image

## start a valkey instance

```console
$ docker run --name some-valkey -d valkey/valkey:unstable
```

## start with persistent storage

```console
$ docker run --name some-valkey -d valkey/valkey:unstable valkey-server --save 60 1 --loglevel warning
```

There are several different persistence strategies to choose from. This one will save a snapshot of the DB every 60 seconds if at least 1 write operation was performed (it will also lead to more logs, so the `loglevel` option may be desirable). If persistence is enabled, data is stored in the `VOLUME /data`, which can be used with `--volumes-from some-volume-container` or `-v /docker/host/dir:/data` (see [docs.docker volumes](https://docs.docker.com/engine/tutorials/dockervolumes/)).

## connecting via `valkey-cli`

```console
$ docker run -it --network some-network --rm valkey/valkey:unstable valkey-cli -h some-valkey
```

## Additionally, If you want to use your own valkey.conf ...

You can create your own Dockerfile that adds a valkey.conf from the context into /data/, like so.

```dockerfile
FROM valkey
COPY valkey.conf /usr/local/etc/valkey/valkey.conf
CMD [ "valkey-server", "/usr/local/etc/valkey/valkey.conf" ]
```

Alternatively, you can specify something along the same lines with `docker run` options.

```console
$ docker run -v /myvalkey/conf:/usr/local/etc/valkey --name myvalkey valkey/valkey:unstable valkey-server /usr/local/etc/valkey/valkey.conf
```

Where `/myvalkey/conf/` is a local directory containing your `valkey.conf` file. Using this method means that there is no need for you to have a Dockerfile for your valkey container.

The mapped directory should be writable, as depending on the configuration and mode of operation, Valkey may need to create additional configuration files or rewrite existing ones.

# License

View [license information](https://github.com/valkey-io/valkey/blob/unstable/COPYING) for the software contained in this image.

As with all Docker images, these likely also contain other software which may be under other licenses (such as Bash, etc from the base distribution, along with any direct or indirect dependencies of the primary software being contained).

As for any pre-built image usage, it is the image user's responsibility to ensure that any use of this image complies with any relevant licenses for all software contained within.