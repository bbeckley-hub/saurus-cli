#!/usr/bin/env bash
# package_data.sh — Package the local data/ folder for saurus init

set -e

VERSION="${1:-v1.0.0}"
DATA_DIR="$(pwd)/data"
DIST_DIR="$(pwd)/dist"

if [ ! -d "$DATA_DIR" ]; then
    echo "❌ Error: data/ folder not found in current directory."
    exit 1
fi

echo "▶ Packaging data version $VERSION..."
mkdir -p "$DIST_DIR"

# 1. Add the DATA_VERSION file inside the data folder
echo "$VERSION" > "$DATA_DIR/DATA_VERSION"

# 2. Create the ZIP (from inside the data/ folder so the root is flat)
cd "$DATA_DIR"
zip -r "$DIST_DIR/saurus_data.zip" . -x ".*" -x "__MACOSX"
cd ..

# 3. Compute SHA256 checksum
cd "$DIST_DIR"
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum saurus_data.zip > saurus_data.zip.sha256
else
    shasum -a 256 saurus_data.zip > saurus_data.zip.sha256
fi
cd ..

echo ""
echo "✅ Package created!"
echo "   ZIP:     $DIST_DIR/saurus_data.zip"
echo "   SHA256:  $DIST_DIR/saurus_data.zip.sha256"
ls -lh "$DIST_DIR"
