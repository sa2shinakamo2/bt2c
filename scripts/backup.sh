#!/bin/bash
    
# Blockchain backup
tar -czf backups/blockchain/backup-$(date +%Y%m%d-%H%M%S).tar.gz data/blockchain

# State backup
tar -czf backups/state/backup-$(date +%Y%m%d-%H%M%S).tar.gz data/state

# Validator backup (encrypted)
tar -czf - validator/keys | gpg --encrypt -r validator@bt2c.com > backups/validator/backup-$(date +%Y%m%d-%H%M%S).tar.gz.gpg

# Cleanup old backups
find backups/blockchain -type f -mtime +30 -delete
find backups/state -type f -mtime +30 -delete
find backups/validator -type f -mtime +30 -delete
