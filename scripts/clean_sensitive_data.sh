#!/bin/bash

# This script helps remove sensitive data from git history

# Remove any files containing sensitive data
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch \
    node/src/wallet.js \
    .env* \
    **/config*.json \
    **/*secret* \
    **/*private* \
    **/wallet.json \
    **/*.pem \
    **/*.key \
    **/*.keystore \
    **/*.p12 \
    **/*.pfx \
    **/*password* \
    **/*token* \
    **/*.env \
    **/.env.* \
    **/id_* \
    **/known_hosts" \
  --prune-empty -- --all

# Force garbage collection and remove old refs
git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive
