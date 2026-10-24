#!/bin/bash
# Regenerates the model-server-grpc mTLS chain: CA, server cert, client cert,
# plus the unsealed and sealed Kubernetes Secret. Run from anywhere; output
# lands in a folder named after the server's hostname (from cert.conf).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
CONF=cert.conf

HOST=$(awk '/\[ *server_dn *\]/{f=1;next} /^\[/{f=0} f && /^CN *=/{sub(/^CN *= */,""); print; exit}' "$CONF")
if [ -z "$HOST" ]; then
  echo "Could not find CN under [ server_dn ] in $CONF" >&2
  exit 1
fi

mkdir -p "$HOST"
cd "$HOST"
CONF="../$CONF"

echo "== Output folder: $HOST =="

echo "== CA =="
openssl genrsa -out ca.key 2048
openssl req -x509 -new -key ca.key -days 3650 -sha256 -config "$CONF" -section ca_req -extensions ca_ext -out ca.crt

echo "== Server cert ($HOST) =="
openssl genrsa -out server.key 2048
openssl req -new -key server.key -config "$CONF" -section server_req -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 1825 -sha256 \
  -extfile "$CONF" -extensions server_ext -out server.crt

echo "== Client cert (CN=client) =="
openssl genrsa -out client.key 2048
openssl req -new -key client.key -config "$CONF" -section client_req -out client.csr
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 1825 -sha256 \
  -extfile "$CONF" -extensions client_ext -out client.crt

rm -f server.csr client.csr ca.srl

echo
echo "Done. Generated in $HOST/: ca.crt ca.key server.crt server.key client.crt client.key"
echo "Verifying chain:"
openssl verify -CAfile ca.crt server.crt
openssl verify -CAfile ca.crt client.crt

echo
echo "== Building the Kubernetes Secret (unsealed) =="
cat > model-server-tls-secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
  namespace: marketinsights
type: kubernetes.io/tls
data:
  tls.crt: $(base64 -i server.crt | tr -d '\n')
  tls.key: $(base64 -i server.key | tr -d '\n')
  ca.crt: $(base64 -i ca.crt | tr -d '\n')
EOF
echo "Wrote $HOST/model-server-tls-secret.yaml"

echo
echo "== Sealing it (requires kubectl access to the cluster's sealed-secrets controller) =="
kubeseal --format yaml < model-server-tls-secret.yaml > model-server-tls-sealed-secret.yaml
echo "Wrote $HOST/model-server-tls-sealed-secret.yaml"
