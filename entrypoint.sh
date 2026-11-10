#!/bin/sh
# saurus-entrypoint — seed /data volume from bundled data on first run,
# then hand off to the CLI.
#
# Behaviour:
#   - No /data mount       → use bundled data at /usr/local/share/saurus/data
#   - /data mount, empty   → seed from bundled data, use /data
#   - /data mount, has data → use /data (persists `saurus init` updates)
#
# Handles argument forms:
#   image                              → saurus --version
#   image --lineage USA300 --count     → saurus --lineage USA300 --count
#   image saurus --lineage USA300      → saurus --lineage USA300
#   image init                         → saurus init
#   image bash                         → bash

set -e

# --- Seed /data if mounted and empty ---
if [ -d /data ]; then
    if [ -z "$(ls -A /data 2>/dev/null)" ]; then
        echo "[saurus-entrypoint] Seeding /data from bundled data..." >&2
        cp -r /usr/local/share/saurus/data/. /data/ 2>/dev/null || true
    fi
    # Point the CLI at /data if it contains anything
    if [ -d /data/mrsa ] || [ -f /data/mrsa_all.tsv ] || [ -f /data/mrsa_all.tsv.gz ]; then
        export SAURUS_DATA_DIR=/data
        echo "[saurus-entrypoint] Using data at /data" >&2
    fi
fi

# --- Default to --version if no args ---
if [ "$#" -eq 0 ]; then
    set -- --version
fi

# --- Prepend "saurus" for flag-style and known subcommands ---
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
