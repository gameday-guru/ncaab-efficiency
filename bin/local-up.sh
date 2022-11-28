#!/bin/bash
export CONTAINER_NAME="gdg-ncaab-efficiency-local"
export VERSION="0.0.0"
docker compose -f ./.docker/alpine-august-tiger/alpine-august-tiger.yml up