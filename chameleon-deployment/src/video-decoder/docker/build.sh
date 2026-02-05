#!/bin/sh

version=$1

if [ -z "${version}" ]; then
    echo "You must provide a version string eg. 1.0.0"
    exit 1
fi

echo "Building..."

for service in client server; do
    if ! docker buildx build --push -t devlew/"${service}"-video-decoder:v"${version}" -f ./"${service}"-dockerfile ..; then
        exit 1
    fi
done

echo "Done"
