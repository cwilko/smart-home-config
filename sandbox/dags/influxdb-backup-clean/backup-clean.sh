#! /bin/bash
# Configmap cmd:
# kubectl create configmap backup-clean-config -n storage --dry-run=client --from-file=backup-clean.sh=backup-clean.sh  -o yaml > backup-clean-config.yaml
# Deletes any backups older than a month. Backups are currently scheduled once per week.

sshpass -p ${NAS_PASSWORD} ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_HOST} '''find /home/kubernetes/storage-influxdb-backup*/ -type f -mtime +30 -execdir rm -v -- '{}' \;'''
echo "Cleanup complete"