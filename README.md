# valkey-container

This Project is the Git repo of the [Valkey "Official Image"](https://hub.docker.com/r/valkey/valkey/)

The Project is now maintained by [the Valkey Community](https://github.com/valkey-io/valkey/)
and it was forked from [docker-library/redis](https://github.com/docker-library/redis).

## When should you build and publish new Docker Image?

You should build and publish a new Docker Image after a new major, minor or patch version of Valkey is released on the [main Valkey repository](https://github.com/valkey-io/valkey).

## How do you build and publish new version of a Docker Image?

*Pre-requisites: [Fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) this repo, create a private Docker Hub repo, and setup your GitHub secrets to access the private Docker Hub repo.*

1. Validate that the metadata for the new version is updated  the [Valkey hashes file](https://github.com/valkey-io/valkey-hashes/blob/main/README). If it is not updated, please open an issue [here](https://github.com/valkey-io/valkey-hashes/issues)
2. If a new major or minor version is released, please create a new directory in the `valkey-container` repo. For example: [`7.2`](https://github.com/valkey-io/valkey-container/tree/mainline/7.2).
3. Run the `update.sh` script locally which will update `versions.json`. It will also populate the Dockerfiles for the new versions in the respective directories. Running the `update.sh` file executes `versions.sh` which updates `versions.json` with the required metadata from the [Valkey hashes file](https://github.com/valkey-io/valkey-hashes/blob/main/README). Once `versions.json` is updated, `apply-templates.sh` is executed which updates Dockerfiles for all the versions directories in the repo. For example [`7.2`](https://github.com/valkey-io/valkey-container/tree/mainline/7.2).
4. Validate that the version and the info is populated correctly from the [Valkey hashes file](https://github.com/valkey-io/valkey-hashes/blob/main/README).
5. Verify all the tests pass on your fork and that your private Docker Hub repository has been updated.
6. Update the `dockerhub-description.md` with the updated tags in your private Docker Hub registry and the Dockerfile links.
7. Publish a PR with these changes. For example: [#8](https://github.com/valkey-io/valkey-container/pull/8)
8. Once the PR is merged, Sit back, relax and enjoy looking at your creation getting published to the official Docker Hub page.
