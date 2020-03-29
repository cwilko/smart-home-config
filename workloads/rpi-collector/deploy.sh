kubectl delete -f telegraf-config.yaml
kubectl delete -f telegraf-deployment.yaml
kubectl delete -f telegraf-rbac.yaml
kubectl apply -f telegraf-rbac.yaml
kubectl apply -f telegraf-config.yaml
kubectl apply -f telegraf-deployment.yaml
