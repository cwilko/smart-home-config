#! /bin/bash

scp *.json root@192.168.1.2:/home/kubernetes/grafana-grafana-data/

kubectl delete pod -l app=grafana --namespace=grafana