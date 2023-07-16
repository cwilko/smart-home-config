#! /bin/bash
# Configmap cmd:
# kubectl create configmap backup-clean-config -n storage --dry-run=client --from-file=backup-clean.sh=backup-clean.sh  -o yaml > backup-clean-config.yaml

sshpass -p ${NAS_PASSWORD} ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_HOST} '''find /home/kubernetes/storage-influxdb-backup*/ -type f -mtime +7 -execdir rm -v -- '{}' \;'''