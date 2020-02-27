#!/usr/bin/env bash
if [ -z "$2" ]
then
      echo "Usage is ./build.sh <Dockerfile-Relative-Directory-Path> <Docker-Image-Tag>"
else
      echo "Bulding $2"
      docker build $1 -t $2
fi
