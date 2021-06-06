#! /bin/bash

scp -r settings.js root@192.168.1.2:/home/kubernetes/actions-actions-data/

kubectl delete pod -l app=actions --namespace=actions