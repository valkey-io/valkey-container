#!/bin/bash

imageTests+=(
	[valkey-container]='
		valkey-basics
		valkey-basics-tls
		valkey-basics-config
		valkey-basics-persistent
	'
)