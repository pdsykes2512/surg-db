#!/bin/bash
# Script to generate PWA icons from SVG

cd "$(dirname "$0")"

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
    echo "ImageMagick not found. Installing..."
    sudo apt-get update && sudo apt-get install -y imagemagick
fi

# Generate icons
echo "Generating app icons..."

# 192x192 icon
convert -background none icon.svg -resize 192x192 icon-192.png
echo "✓ Generated icon-192.png"

# 512x512 icon
convert -background none icon.svg -resize 512x512 icon-512.png
echo "✓ Generated icon-512.png"

# Apple touch icon (180x180)
convert -background none icon.svg -resize 180x180 apple-touch-icon.png
echo "✓ Generated apple-touch-icon.png"

echo "✓ All icons generated successfully!"
