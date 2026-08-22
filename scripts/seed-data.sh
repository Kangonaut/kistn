#!/usr/bin/env bash
set -e

echo "generating dummy backup source files ..."

# Define test source directories
BASE_DIR="/root/data"
mkdir -p "$BASE_DIR/books" \
         "$BASE_DIR/covers"

# Populate dummy data
wget "https://github.com/GITenberg/Die-Verwandlung_22367/raw/refs/heads/master/22367-8.txt" -O "$BASE_DIR/books/die-verwandlung.txt"
wget "https://github.com/GITenberg/Die-Verwandlung_22367/blob/master/cover.png?raw=true" -O "$BASE_DIR/covers/die-verwandlung.png"

echo "✔ test environment populated in $BASE_DIR"
