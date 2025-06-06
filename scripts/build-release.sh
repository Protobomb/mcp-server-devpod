#!/bin/bash

# Build release binaries for mcp-server-devpod
# Usage: ./scripts/build-release.sh [version]

set -e

VERSION=${1:-"dev"}
OUTPUT_DIR="./dist"

echo "Building mcp-server-devpod version: $VERSION"

# Clean and create output directory
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Build matrix
declare -a platforms=(
    "linux/amd64"
    "linux/arm64"
    "darwin/amd64"
    "darwin/arm64"
    "windows/amd64"
)

for platform in "${platforms[@]}"; do
    IFS='/' read -r os arch <<< "$platform"
    
    echo "Building for $os/$arch..."
    
    output_name="mcp-server-devpod-$os-$arch"
    if [ "$os" = "windows" ]; then
        output_name="${output_name}.exe"
    fi
    
    # Build binary
    GOOS=$os GOARCH=$arch go build \
        -o "$OUTPUT_DIR/$output_name" \
        -ldflags="-s -w -X main.version=$VERSION" \
        main.go
    
    # Create archive
    cd "$OUTPUT_DIR"
    if [ "$os" = "windows" ]; then
        cp ../README.md ../LICENSE .
        zip "${output_name%.exe}.zip" "$output_name" README.md LICENSE
        rm README.md LICENSE
    else
        cp ../README.md ../LICENSE .
        tar czf "${output_name}.tar.gz" "$output_name" README.md LICENSE
        rm README.md LICENSE
    fi
    cd ..
    
    echo "✓ Built $output_name"
done

echo ""
echo "Release binaries built in $OUTPUT_DIR:"
ls -la "$OUTPUT_DIR"

echo ""
echo "To test a binary:"
echo "  $OUTPUT_DIR/mcp-server-devpod-linux-amd64 --version"