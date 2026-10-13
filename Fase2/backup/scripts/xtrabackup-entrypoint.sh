#!/bin/sh
set -eu

# Windows bind mounts can appear world-writable inside Linux containers.
# Copy the credentials to a private container file before XtraBackup reads it.
cp /run/config/xtrabackup.cnf /tmp/xtrabackup.cnf
cp /run/config/backup-encryption.key /tmp/backup-encryption.key
chmod 600 /tmp/xtrabackup.cnf /tmp/backup-encryption.key

exec xtrabackup --defaults-extra-file=/tmp/xtrabackup.cnf "$@"
