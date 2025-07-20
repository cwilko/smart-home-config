# NGINX Ingress Controller Configuration

Modern NGINX Ingress Controller v1.12.3 deployment for smart home Kubernetes cluster.

## Files Overview

### `customized-deploy.yaml`
**Purpose**: Complete NGINX Ingress Controller deployment with LoadBalancer service

**Kubernetes Resources:**
- `Namespace/ingress-nginx` - Dedicated namespace for NGINX controller resources
- `ServiceAccount/ingress-nginx` - Service account for the controller pod to access Kubernetes API
- `Role/ingress-nginx` - Namespace-scoped permissions for managing ingresses and secrets
- `ClusterRole/ingress-nginx` - Cluster-wide permissions for reading nodes, services, and ingresses
- `RoleBinding/ingress-nginx` - Binds the namespace role to the service account
- `ClusterRoleBinding/ingress-nginx` - Binds the cluster role to the service account
- `ConfigMap/ingress-nginx-controller` - Configuration settings for the NGINX controller
- `Service/ingress-nginx-controller` - LoadBalancer service exposing NGINX on IP 192.168.1.203
- `Deployment/ingress-nginx-controller` - The main NGINX controller pod deployment
- `IngressClass/nginx` - Defines this controller as the handler for ingress resources with class "nginx"

### `ingress-resources.yaml`
**Purpose**: Application ingress routes with explicit nginx class assignment

**Kubernetes Resources:**
- `Ingress/grafana-ingress` - Routes grafana.192.168.1.203.nip.io to grafana-service:80
- `Ingress/actions-ingress` - Routes actions.192.168.1.203.nip.io to actions-service:80
- `Ingress/marketinsights-api-ingress` - Routes marketinsights-api.192.168.1.203.nip.io to marketinsights-api-service:80
- `Ingress/mi-price-store-ingress` - Routes pricestore.192.168.1.203.nip.io to price-store-service:80
- `Ingress/portfolio-mgr-ingress` - Routes portfolio-mgr.192.168.1.203.nip.io to portfolio-mgr-service:80
- `Ingress/airflow-ingress` - Routes airflow.192.168.1.203.nip.io to airflow-service:80
- `Ingress/model-server-ingress` - Routes model-server.192.168.1.203.nip.io to model-server-http-service:80
- `Ingress/model-server-grpc-ingress` - Routes model-server-grpc.192.168.1.203.nip.io to model-server-grpc-service:8500 with TLS client certificate authentication

### `tls-sealed-secret.yaml`
**Purpose**: TLS certificates for gRPC service client authentication

**Kubernetes Resources:**
- `SealedSecret/tls-secret` - Encrypted TLS certificate and private key for model-server-grpc ingress client authentication

## Deployment

```bash
kubectl apply -f smart-home-config/sandbox/ingress/
```

## Key Features

- **Modern Security**: Non-root containers, read-only filesystems, minimal RBAC permissions
- **LoadBalancer Integration**: Direct MetalLB integration with static IP assignment
- **IngressClass Separation**: Clean separation from Tailscale ingress controller  
- **No Admission Webhooks**: Simplified deployment without validation complexity
- **TLS Support**: Client certificate authentication for gRPC services