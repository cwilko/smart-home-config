#! /bin/bash

scp -r scripts/* root@192.168.1.2:/home/kubernetes/alerting-kapacitor-scripts-pvc*/

kubectl delete pod --all --namespace=alerting