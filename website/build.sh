#!/bin/bash

# Create dist directory
mkdir -p dist

# Copy all necessary files
cp *.html dist/
cp -r css dist/
cp -r js dist/
cp -r images dist/

# Copy other necessary files
cp package.json dist/
cp netlify.toml dist/
