# Build instructions

cd config

wget https://raw.githubusercontent.com/node-red/node-red/master/packages/node_modules/node-red/settings.js

kubectl create configmap actions-config --from-file=settings.js

kubectl get cm actions-config -o yaml > ../actions-config.yaml

