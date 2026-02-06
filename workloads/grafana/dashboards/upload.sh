#! /bin/bash

scp *.json root@192.168.1.72:/mnt/SSD_pool/data/kubernetes/automation-grafana-data/

kubectl delete pod -l app=grafana --namespace=automation