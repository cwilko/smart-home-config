# Nginx Streaming Configuration for Resilient Large File Buffering

## Overview

This configuration enables Nginx to buffer large streaming files (50GB+) ahead of client playback to handle upstream instability seamlessly. The strategy creates a buffer window (e.g., 5GB = ~12 hours protection at 120KB/s) that allows continuous playback even during upstream outages.

## Strategy

```
Upstream (unstable) → Nginx (buffer 5GB ahead) → Client (continuous playback)
                      ↑
                  Handles outages seamlessly
```

**Key Benefits:**
- ✅ Seamless playback through upstream outages
- ✅ Better user experience
- ✅ Handles network instability

**Trade-offs:**
- ❌ High disk usage (50GB per stream)
- ❌ Slower startup (500MB delay before playback starts)
- ❌ Complex configuration

## Nginx Configuration (Standard)

### Basic Resilient Buffering

```nginx
location /stremio-proxy/ {
    proxy_pass http://192.168.1.79:8081;
    
    # Enable buffering (opposite of streaming-only config)
    proxy_buffering on;
    
    # Large buffer configuration
    proxy_buffers 50 100m;              # 50 buffers x 100MB = 5GB
    proxy_buffer_size 100m;             # Initial buffer size
    proxy_busy_buffers_size 500m;       # How much to buffer before sending (1hr ahead)
    
    # Disk buffering for huge files
    proxy_max_temp_file_size 50g;       # Allow 50GB temp files
    proxy_temp_file_write_size 100m;    # Write in 100MB chunks
    
    # Critical: Longer timeouts for buffering
    proxy_read_timeout 24h;             # Wait for upstream
    proxy_send_timeout 24h;             # Send to client
    proxy_connect_timeout 60s;
}
```

### Advanced Configuration with Redundancy

```nginx
# Multiple upstream servers for redundancy
upstream stremio_backend {
    server 192.168.1.79:8081 max_fails=3 fail_timeout=30s;
    server 192.168.1.80:8081 backup;  # Backup server
}

# Configure temp file location
http {
    proxy_temp_path /big-disk/nginx-temp levels=1:2;
}

location /stremio-proxy/ {
    proxy_pass http://stremio_backend;
    
    # Buffering for resilience
    proxy_buffering on;
    proxy_buffers 50 100m;
    proxy_buffer_size 100m;
    proxy_busy_buffers_size 500m;        # 1hr ahead buffer
    
    # Disk spillover
    proxy_max_temp_file_size 50g;
    proxy_temp_file_write_size 100m;
    
    # Upstream failure handling
    proxy_read_timeout 24h;
    proxy_next_upstream error timeout;   # Try next upstream on failure
    proxy_next_upstream_tries 3;         # Retry attempts
    proxy_next_upstream_timeout 30s;     # Time before trying next
    
    # Connection optimization
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    
    # Headers for debugging
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## Kubernetes Nginx Ingress Configuration

### Basic Ingress with Resilient Buffering

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: stremio-proxy-resilient
  annotations:
    kubernetes.io/ingress.class: "nginx"
    
    # Enable buffering (opposite of streaming-only config)
    nginx.ingress.kubernetes.io/proxy-buffering: "on"
    
    # Large buffer configuration
    nginx.ingress.kubernetes.io/proxy-buffers-number: "50"
    nginx.ingress.kubernetes.io/proxy-buffer-size: "100m"
    nginx.ingress.kubernetes.io/proxy-busy-buffers-size: "500m"
    
    # Disk buffering for huge files
    nginx.ingress.kubernetes.io/proxy-max-temp-file-size: "50g"
    nginx.ingress.kubernetes.io/proxy-temp-file-write-size: "100m"
    
    # Timeout configuration
    nginx.ingress.kubernetes.io/proxy-read-timeout: "86400"  # 24h in seconds
    nginx.ingress.kubernetes.io/proxy-send-timeout: "86400"  # 24h in seconds
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"
    
    # Connection optimization
    nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
    
    # Advanced server snippet for additional config
    nginx.ingress.kubernetes.io/server-snippet: |
      proxy_temp_path /tmp/nginx-temp levels=1:2;
      client_max_body_size 0;

spec:
  tls:
  - hosts:
    - squirrelnet.co.uk
    secretName: squirrelnet-tls
  rules:
  - host: squirrelnet.co.uk
    http:
      paths:
      - path: /stremio-proxy
        pathType: Prefix
        backend:
          service:
            name: stremio-backend
            port:
              number: 8081
```

### Advanced Ingress with Upstream Configuration

```yaml
# ConfigMap for custom nginx configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-custom-config
  namespace: ingress-nginx
data:
  proxy-temp-path: "/tmp/nginx-temp levels=1:2"
  upstream-keepalive-timeout: "60s"

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: stremio-proxy-advanced
  annotations:
    kubernetes.io/ingress.class: "nginx"
    
    # Resilient buffering configuration
    nginx.ingress.kubernetes.io/proxy-buffering: "on"
    nginx.ingress.kubernetes.io/proxy-buffers-number: "50"
    nginx.ingress.kubernetes.io/proxy-buffer-size: "100m"
    nginx.ingress.kubernetes.io/proxy-busy-buffers-size: "500m"
    nginx.ingress.kubernetes.io/proxy-max-temp-file-size: "50g"
    nginx.ingress.kubernetes.io/proxy-temp-file-write-size: "100m"
    
    # Timeout configuration
    nginx.ingress.kubernetes.io/proxy-read-timeout: "86400"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "86400"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"
    
    # Upstream failure handling
    nginx.ingress.kubernetes.io/upstream-max-fails: "3"
    nginx.ingress.kubernetes.io/upstream-fail-timeout: "30s"
    
    # Custom configuration snippet
    nginx.ingress.kubernetes.io/configuration-snippet: |
      proxy_next_upstream error timeout;
      proxy_next_upstream_tries 3;
      proxy_next_upstream_timeout 30s;
      
      # Headers for debugging
      proxy_set_header X-Buffer-Status $upstream_cache_status;
      proxy_set_header X-Response-Time $upstream_response_time;

spec:
  tls:
  - hosts:
    - squirrelnet.co.uk
    secretName: squirrelnet-tls
  rules:
  - host: squirrelnet.co.uk
    http:
      paths:
      - path: /stremio-proxy
        pathType: Prefix
        backend:
          service:
            name: stremio-backend
            port:
              number: 8081
```

## Key Configuration Parameters Explained

### Buffer Settings
- **`proxy_buffers 50 100m`**: 50 buffers × 100MB = 5GB total buffer capacity
- **`proxy_busy_buffers_size 500m`**: Start sending to client after 500MB buffered (creates 1hr protection window)
- **`proxy_buffer_size 100m`**: Initial buffer for response headers

### Disk Configuration
- **`proxy_max_temp_file_size 50g`**: Maximum temp file size per request
- **`proxy_temp_file_write_size 100m`**: Write temp files in 100MB chunks
- **`proxy_temp_path`**: Location for temporary files (ensure sufficient disk space)

### Timeline Example
```
T+0s:    Client requests → Nginx starts buffering from upstream
T+30s:   Nginx has 500MB buffered → Starts sending to client  
T+60s:   Client playing, Nginx continues buffering ahead
T+300s:  Upstream goes down → Client keeps playing from buffer
T+600s:  Upstream comes back → Nginx resumes filling buffer
```

## Storage Considerations

**Disk usage calculation:**
- 5 concurrent 50GB streams = 250GB temp space needed
- Default location: `/var/cache/nginx/proxy_temp/`
- Ensure adequate disk space on temp path

**Monitoring commands:**
```bash
# Watch temp files being created
watch -n 1 'ls -lh /var/cache/nginx/proxy_temp/'

# Monitor disk usage
df -h /var/cache/nginx/

# Check buffer effectiveness in logs
tail -f /var/log/nginx/access.log | grep "proxy_temp"
```

## SSL Certificate Setup for Kubernetes

```bash
# Create TLS secret from existing certificate
kubectl create secret tls squirrelnet-tls \
  --cert=/path/to/your/cert.pem \
  --key=/path/to/your/private.key \
  --namespace=default
```

## Alternative: Non-Buffering Configuration

If disk space is limited, use the streaming-only configuration:

```nginx
# For immediate streaming without buffering
location /stremio-proxy/ {
    proxy_pass http://192.168.1.79:8081;
    
    # Disable buffering for direct streaming
    proxy_buffering off;
    proxy_request_buffering off;
    
    # Long timeouts still needed
    proxy_read_timeout 24h;
    proxy_send_timeout 24h;
    proxy_connect_timeout 60s;
    
    # Connection optimization
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_cache off;
    client_max_body_size 0;
}
```

## Implementation Notes

1. **Test with small files first** to validate configuration
2. **Monitor disk space** closely during implementation
3. **Consider backup upstream servers** for additional resilience
4. **Adjust buffer sizes** based on your specific outage patterns and storage capacity
5. **Set up monitoring** for temp file usage and upstream health

## Troubleshooting

- **High disk usage**: Reduce `proxy_buffers` or `proxy_max_temp_file_size`
- **Slow startup**: Reduce `proxy_busy_buffers_size`
- **Still getting timeouts**: Check `proxy_read_timeout` and upstream health
- **Out of disk space**: Configure `proxy_temp_path` to larger disk or reduce concurrent streams