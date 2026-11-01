#!/bin/sh
# Copy the canonical category and tag lists into the Chrome clipper, so it always
# offers the same vocabulary as the app. Run by Scripts/build-mac.sh; also safe to
# run by hand. The files in Scripts/catalogue are the single source of truth.
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
src="$root/Scripts/catalogue"
dest="$root/chrome-clipper/vocab"
mkdir -p "$dest"
cp "$src/categories.json" "$dest/categories.json"
cp "$src/tags.json" "$dest/tags.json"
echo "Synced clipper vocab into chrome-clipper/vocab/"
