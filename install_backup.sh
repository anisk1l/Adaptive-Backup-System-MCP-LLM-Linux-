#!/usr/bin/env bash

sudo apt update
sudo apt install dos2unix tar notify-osd -y

mkdir -p /var/log
touch /var/log/adaptive_backup.log

dos2unix easy_backup.sh
chmod +x easy_backup.sh

echo "=== INSTALL COMPLETE ==="
echo "Run: ./easy_backup.sh"
