#!/bin/bash

original_tags='[
  valkey-container:unstable,
  valkey-container:unstable-bookworm
]'

converted_list=$(echo $original_tags | sed 's/valkey-container/valkey\/valkey/g'| sed 's/\[ *//; s/ *\]//; s/ //g')
echo $converted_list

