# Tailscale Kubernetes Operator

This directory contains configuration for deploying the Tailscale Kubernetes Operator as an alternative to sidecar containers.

## Benefits Over Sidecar Approach

- ✅ **No privileged app containers** - Only operator has network privileges
- ✅ **No host mounts** - App pods completely isolated  
- ✅ **Standard Kubernetes patterns** - Uses Ingress resources
- ✅ **Future Funnel ready** - Easy to add public access later
- ✅ **Better security** - Reduced attack surface per workload
- ✅ **Central management** - One operator handles all Tailscale networking

## Files

- `operator.yaml` - Main Tailscale operator deployment (downloaded from GitHub)
- `tailscale-sealed-secret.yaml` - Sealed secret for OAuth credentials
- `oauth-tag-configuration.md` - IMPORTANT: Correct OAuth client tag setup
- `README.md` - This file

## Installation Steps

### 1. Create OAuth Credentials

1. Go to https://login.tailscale.com/admin/settings/oauth
2. Click **"Generate OAuth Client"**
3. Configure:
   - **Name**: `Kubernetes Operator`
   - **Scopes** (select "write" for each): 
     - `devices:core` (write)
     - `devices:routes` (write)
     - `policy_file` (write)
     - `dns:write` (if using DNS features)
   - **Tags**: 
     - `tag:k8s-operator` (ONLY this tag - do not add `tag:k8s`)
4. Save the `client_id` and `client_secret`

### 2. Create Sealed Secrets

```bash
# Option 1: Using --raw flag (Recommended)
echo -n "k123456789" | kubeseal --raw --from-file=/dev/stdin --namespace=tailscale --name=operator-oauth --scope=strict
echo -n "tskey-client-xyz..." | kubeseal --raw --from-file=/dev/stdin --namespace=tailscale --name=operator-oauth --scope=strict

# Option 2: Create secret first, then seal it
kubectl create secret generic operator-oauth \
  --namespace=tailscale \
  --from-literal=client_id="k123456789" \
  --from-literal=client_secret="tskey-client-xyz..." \
  --dry-run=client -o yaml | kubeseal --format=yaml
```

### 3. Update oauth-secret.yaml

Replace the placeholder encrypted values in `oauth-secret.yaml` with your actual sealed secrets.

### 4. Deploy Operator

```bash
# Apply OAuth secret first
kubectl apply -f oauth-secret.yaml

# Deploy operator
kubectl apply -f operator.yaml
```

### 5. Verify Installation

```bash
# Check operator logs
kubectl logs -n tailscale deployment/operator

# Verify operator joined tailnet
# Look for "tailscale-operator" device in admin console at:
# https://login.tailscale.com/admin/machines
```

## Using the Operator

### Expose Service to Tailnet

Add annotation to your service:

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    tailscale.com/expose: "true"
spec:
  # ... service configuration
```

### Expose Service via Ingress

Create an Ingress resource:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-service-ingress
  annotations:
    # For internal Tailscale access only
    tailscale.com/expose: "true"
    
    # For public internet access (add later)
    # tailscale.com/funnel: "true"
spec:
  ingressClassName: tailscale
  rules:
  - host: my-service
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-service
            port:
              number: 80
```

## Security Considerations

### Operator Security
- Operator runs with networking privileges in `tailscale` namespace
- Monitor operator pod for security issues
- Keep operator updated regularly
- Apply network policies to restrict operator access

### OAuth Credential Security
- OAuth credentials provide admin access to your tailnet
- Store securely using sealed secrets
- Rotate credentials regularly
- Monitor device creation in admin console

## Troubleshooting

### OAuth Permission Errors (403)
If you see "calling actor does not have enough permissions":
- See detailed guide: `troubleshooting-oauth.md`
- Verify OAuth scopes have **write** permissions
- Ensure tags (`tag:k8s-operator`, `tag:k8s`) are configured
- Check Tailscale policy includes tagOwners

### Operator Won't Start
```bash
# Check operator logs
kubectl logs -n tailscale deployment/operator

# Check if OAuth secret exists
kubectl get secret -n tailscale operator-oauth

# Verify secret contents (base64 decode to check)
kubectl get secret -n tailscale operator-oauth -o yaml
```

### Device Not Appearing in Admin Console
- Verify OAuth scopes include `devices:core` with **write** permission
- Check for authentication errors in operator logs
- Ensure client_secret is correctly encrypted

### Service Not Accessible via Tailscale
- Verify service has correct annotation
- Check proxy pod is created: `kubectl get pods -n <your-namespace>`
- Check proxy pod logs: `kubectl logs -n <your-namespace> <proxy-pod>`

## Updating the Operator

To update to a newer version:

```bash
# Download latest manifest
curl -s https://raw.githubusercontent.com/tailscale/tailscale/main/cmd/k8s-operator/deploy/manifests/operator.yaml > operator.yaml

# Apply update
kubectl apply -f operator.yaml
```

## Migration from Sidecar

If migrating from sidecar containers:

1. Deploy operator first
2. Update service configuration to use operator
3. Remove sidecar containers from deployment
4. Remove privileged security contexts
5. Remove host volume mounts