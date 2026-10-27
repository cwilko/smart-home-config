#!/bin/bash
# Regenerates the webhook CA and serving cert for the optional Fission admission webhook
# (workloads/fission/optional/webhook-server.yaml), as one unsealed and one sealed Secret in secrets/. Run from anywhere;
# certs and keys land next to this script. Re-running rotates everything, so re-apply the sealed secret and restart the
# webhook pod afterwards. Re-run workloads/fission/generate-yamls.sh afterwards if ca.crt changed.
# Fission's internal auth is turned off (internalAuth.enabled: false in helm-values.yaml), so there is no
# fission-internal-auth Secret.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

OUT=secrets
NS=automation

b64() { base64 -i "$1" | tr -d '\n'; }

echo "== CA =="
openssl genrsa -out ca.key 2048
openssl req -x509 -new -key ca.key -days 1825 -sha256 -subj "/CN=fission-ca" -out ca.crt

echo "== Webhook serving cert (webhook-service.$NS.svc) =="
openssl genrsa -out webhook.key 2048
openssl req -new -key webhook.key -subj "/CN=webhook-service.$NS.svc" -out webhook.csr
printf "subjectAltName=DNS:webhook-service.%s.svc,DNS:webhook-service.%s.svc.cluster.local\nextendedKeyUsage=serverAuth\n" "$NS" "$NS" > webhook.ext
openssl x509 -req -in webhook.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 1825 -sha256 \
  -extfile webhook.ext -out webhook.crt

rm -f webhook.csr webhook.ext ca.srl

echo
echo "Verifying chain:"
openssl verify -CAfile ca.crt webhook.crt

echo
echo "== Building the Kubernetes Secret (unsealed) =="
mkdir -p "$OUT"
cat > "$OUT/webhook-certs-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: fission-webhook-certs
  namespace: $NS
type: Opaque
data:
  ca.crt: $(b64 ca.crt)
  tls.crt: $(b64 webhook.crt)
  tls.key: $(b64 webhook.key)
EOF
echo "Wrote $OUT/webhook-certs-secret.yaml"

echo
echo "== Sealing it (requires kubectl access to the cluster's sealed-secrets controller) =="
kubeseal --format yaml < "$OUT/webhook-certs-secret.yaml" > "$OUT/webhook-certs-sealed-secret.yaml"
echo "Wrote $OUT/webhook-certs-sealed-secret.yaml"
