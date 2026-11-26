#!/bin/sh
# saurus-entrypoint — seed /data from bundled data on first run.
set -e

# If /data is mounted, point the CLI at it
if [ -d /data ]; then
    export SAURUS_DATA_DIR=/data
fi

# Skip seeding when running init (user is explicitly installing data)
skip_seed=0
case "$1" in
    init|setup) skip_seed=1 ;;
    saurus)
        case "$2" in
            init|setup) skip_seed=1 ;;
        esac
        ;;
esac

# Seed /data only if mounted, empty, and not running init
if [ -d /data ] && [ "$skip_seed" = "0" ] && [ -z "$(ls -A /data 2>/dev/null)" ]; then
    echo "[saurus-entrypoint] Seeding /data from bundled data..." >&2
    cp -r /usr/local/share/saurus/data/. /data/ 2>/dev/null || true
fi

if [ "$#" -eq 0 ]; then
    set -- --version
fi

case "$1" in
    --*|init|setup)
        exec saurus "$@"
        ;;
    saurus)
        shift
        exec saurus "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
