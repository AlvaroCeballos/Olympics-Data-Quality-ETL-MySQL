#!/bin/sh
set -eu

# Windows bind mounts can appear world-writable inside Linux containers.
# Copy the credentials to a private container file before XtraBackup reads it.
cp /run/config/xtrabackup.cnf /tmp/xtrabackup.cnf
chmod 600 /tmp/xtrabackup.cnf

exec xtrabackup --defaults-extra-file=/tmp/xtrabackup.cnf "$@"
