#! /bin/bash

scp -r ../../scripts/* root@192.168.1.72:/mnt/SSD_pool/data/kubernetes/automation-kapacitor-scripts/

kubectl delete pod -l app=kapacitor --namespace=automation