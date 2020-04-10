#! /bin/bash

scp *.tick root@192.168.1.2:/home/kubernetes/alerting-kapacitor-scripts-pvc*/

kubectl delete --all-pods --namespace=alerting