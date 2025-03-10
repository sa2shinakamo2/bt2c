#!/bin/bash

# Clean dist directory if it exists
rm -rf dist

# Create dist directory
mkdir -p dist

# Copy all HTML files
cp *.html dist/

# Copy static assets
cp -r css dist/
cp -r js dist/
cp -r images dist/
cp -r docs dist/  # Ensure docs directory is copied

# Process documentation files
if [ -f "../docs/VALIDATOR_GUIDE.md" ]; then
  mkdir -p dist/docs
  cp ../docs/VALIDATOR_GUIDE.md dist/docs/
fi

# Copy configuration files
cp package.json dist/
cp netlify.toml dist/

# Ensure proper permissions
chmod -R 755 dist
