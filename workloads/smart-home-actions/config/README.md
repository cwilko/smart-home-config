# settings.js & flows.json

	cd config

	wget https://raw.githubusercontent.com/node-red/node-red/master/packages/node_modules/node-red/settings.js

flows.json must be retrieved or exported from a running Node-red instance

Make any updates at this point..

	kubectl create configmap actions-config -n actions --dry-run --from-file=settings.js=settings.js --from-file=flows.json=flows.json -o yaml > actions-config.yaml

# flows_cred.json

This file must first be retrieved from a running Node-red instance

To create the sealed-secret file

    kubectl create secret generic node-red-secret -n actions --dry-run --from-file=flows_cred.json=flows_cred.json -o yaml > /tmp/node-red-secret.yaml

    kubeseal < /tmp/node-red-secret.yaml -o yaml > node-red-sealed-secret.yaml

