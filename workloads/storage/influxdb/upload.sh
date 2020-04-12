#! /bin/bash

scp -r data/* root@192.168.1.2:/home/kubernetes/storage-influxdb-data-pvc*/

#kubectl exec -it influxdb-deployment-6dd74886b7-htrcj -n storage -- sh /var/lib/influxdb/clear_subs.sh
