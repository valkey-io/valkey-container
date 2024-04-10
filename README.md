This Project is the Git repo of the [Valkey "Official Image"](https://hub.docker.com/r/valkey/valkey/)

The Project is now maintained by [the Valkey Community](https://github.com/valkey-io/valkey/) 
and it was forked from https://github.com/docker-library/redis.

## How to build and publish new version Docker Image?
*Pre-requisites: Fork this repo, create a private dockerhup repo and setup the Github secrets to access the private dockerhup repo.*
1. Validate if the metadata for the new version is updated at https://github.com/valkey-io/valkey-hashes/blob/main/README
2. If its a new major version create a new dir. For example `7.2`.
3. Run the `update.sh` script locally, which will update the `versions.json` and also populate the Dockerfiles for the new versions in the repective directories.
4. Validate if the version and the info is populated correctly.
5. See if all the tests pass on your fork and the your private docker up has been updated. 
5. Publish a PR with these changes. For example: https://github.com/valkey-io/valkey-container/pull/8
6. Once the PR is merged, Sit back, relax and enjoy looking at your creation getting publish to the official Docker hub page. 