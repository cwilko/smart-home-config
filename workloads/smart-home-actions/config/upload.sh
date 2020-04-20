#! /bin/bash

scp -r flows.json root@192.168.1.2:/home/kubernetes/actions-actions-data-pvc*/

kubectl delete pod -l app=actions --namespace=actions