#!/bin/bash

# Script to clean sensitive data from Git repository history
echo "Starting repository cleaning process..."

# Create a backup branch
git checkout -b backup_before_cleaning

# Return to main branch
git checkout main

# Use git filter-branch to remove sensitive files from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch \
   testnet/data/validator1_wallet.json \
   testnet/data/developer_wallet.json \
   testnet/data/validator2_wallet.json \
   testnet/data/user_wallet.json \
   wallets/6FNE6RW6FHTVQJDK7KTADYC7OBA3OIQ3PBOUM35W.json \
   testnet/certs/validator-1.key \
   testnet/certs/validator-2.key \
   testnet/certs/validator-3.key \
   testnet/certs/validator-4.key \
   testnet/certs/validator-5.key" \
  --prune-empty --tag-name-filter cat -- --all

echo "Repository cleaning complete."
echo "IMPORTANT: You must now force-push to the remote repository:"
echo "git push origin --force --all"
echo ""
echo "After force-pushing, all collaborators must run:"
echo "git fetch origin"
echo "git reset --hard origin/main"
echo ""
echo "SECURITY REMINDER: You must rotate all exposed private keys!"
