This Project is the Git repo of the [Valkey "Official Image"](https://hub.docker.com/r/valkey/valkey/)

The Project is now maintained by [the Valkey Community](https://github.com/valkey-io/valkey/)
and it was forked from https://github.com/docker-library/redis.

## When to build and publish new Docker Image?

After a new major, minor or patch version of Valkey is released on https://github.com/valkey-io/valkey.

## How to build and publish new version Docker Image?

*Pre-requisites: [Fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) this repo, create a private dockerhub repo and setup the Github secrets to access the private dockerhub repo.*

1. Validate if the metadata for the new version is updated at https://github.com/valkey-io/valkey-hashes/blob/main/README - If it is not updated, please open an issue here https://github.com/valkey-io/valkey-hashes/issues
2. If a new major or minor version is released, please create a new dir in the `valkey-container` repo. For example [`7.2`](https://github.com/valkey-io/valkey-container/tree/mainline/7.2).
3. Run the `update.sh` script locally, which will update the `versions.json` and also populate the Dockerfiles for the new versions in the respective directories. Running the `update.sh` file, executes the `versions.sh` which updates the `versions.json` file with the required metadata from https://github.com/valkey-io/valkey-hashes/blob/main/README. Once `versions.json` is updated, `apply-templates.sh` is executed which updates Docker files for all the versions directories in the repo (For example, [`7.2`](https://github.com/valkey-io/valkey-container/tree/mainline/7.2)).
4. Validate if the version and the info is populated correctly from the https://github.com/valkey-io/valkey-hashes/blob/main/README file.
5. See if all the tests pass on your fork and the your private docker hub has been updated.
6. Update the `dockerhub-description.md` with the updated tags in your private docker hub and the Docker files links.
7. Publish a PR with these changes. For example: https://github.com/valkey-io/valkey-container/pull/8
8. Once the PR is merged, Sit back, relax and enjoy looking at your creation getting published to the official Docker hub page.
