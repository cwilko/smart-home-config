# InfluxDB Kubernetes Metrics Reference

This document describes the Kubernetes metrics available in your InfluxDB telegraf database, collected by the Telegraf Kubernetes plugin.

## Overview

InfluxDB Version: **1.7.10**
Database: **telegraf**
Source: Telegraf Kubernetes input plugin

## Available Measurements

### 1. kubernetes_pod_container

Most detailed container-level metrics for monitoring individual pod containers.

**Fields:**
- `cpu_usage_nanocores` - CPU usage in nanocores (divide by 1,000,000 for millicores)
- `cpu_usage_core_nanoseconds` - Cumulative CPU usage
- `memory_working_set_bytes` - Active memory usage
- `memory_rss_bytes` - Resident set size
- `memory_usage_bytes` - Total memory usage
- `memory_page_faults` - Page fault count
- `rootfs_used_bytes` - Container filesystem usage
- `rootfs_available_bytes` - Available filesystem space
- `logsfs_used_bytes` - Log filesystem usage
- `resource_limits_millicpu_units` - CPU limit
- `resource_limits_memory_bytes` - Memory limit
- `resource_requests_millicpu_units` - CPU request
- `resource_requests_memory_bytes` - Memory request
- `restarts_total` - Container restart count
- `ready` - Container ready status (0 or 1)
- `state_code` - Container state code

**Tags:**
- `namespace` - Pod namespace
- `pod_name` - Pod name
- `container_name` - Container name
- `node_name` - Node running the pod
- `image` - Container image
- `phase` - Pod phase (Running, Pending, etc.)
- `state` - Container state

**Example Queries:**

```bash
# Check CPU and memory for all containers in automation namespace
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name, cpu_usage_nanocores, memory_working_set_bytes
   FROM kubernetes_pod_container
   WHERE namespace='automation'
   ORDER BY time DESC LIMIT 10"

# Find containers using most memory
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name, memory_working_set_bytes
   FROM kubernetes_pod_container
   WHERE time > now() - 1h
   ORDER BY memory_working_set_bytes DESC LIMIT 20"

# Track Airflow scheduler resource usage over time
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT mean(cpu_usage_nanocores)/1000000 as avg_cpu_millicores,
          mean(memory_working_set_bytes)/1048576 as avg_memory_mb
   FROM kubernetes_pod_container
   WHERE pod_name =~ /airflow/ AND container_name='airflow-scheduler'
   AND time > now() - 24h
   GROUP BY time(1h)"

# Check containers with restarts
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name, restarts_total
   FROM kubernetes_pod_container
   WHERE restarts_total > 0
   ORDER BY time DESC LIMIT 10"

# Monitor democratic-csi CPU usage
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name, cpu_usage_nanocores/1000000 as cpu_millicores
   FROM kubernetes_pod_container
   WHERE pod_name =~ /democratic-csi/
   ORDER BY time DESC LIMIT 10"
```

---

### 2. kubernetes_node

Node-level resource metrics.

**Fields:**
- `capacity_cpu_cores` - Total CPU cores
- `capacity_memory_bytes` - Total memory
- `capacity_pods` - Maximum pods
- `allocatable_cpu_cores` - Available CPU cores
- `allocatable_memory_bytes` - Available memory
- `allocatable_pods` - Available pod slots
- `cpu_usage_nanocores` - Current CPU usage
- `memory_working_set_bytes` - Active memory usage
- `memory_available_bytes` - Available memory
- `fs_used_bytes` - Filesystem usage
- `fs_available_bytes` - Available filesystem space
- `network_rx_bytes` - Network bytes received
- `network_tx_bytes` - Network bytes transmitted
- `network_rx_errors` - Network receive errors
- `network_tx_errors` - Network transmit errors
- `ready` - Node ready status
- `status_condition` - Node condition status

**Tags:**
- `node_name` - Node name
- `host` - Host name

**Example Queries:**

```bash
# Check node resource usage
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT node_name,
          cpu_usage_nanocores/1000000 as cpu_millicores,
          memory_working_set_bytes/1073741824 as memory_gb,
          memory_available_bytes/1073741824 as available_gb
   FROM kubernetes_node
   ORDER BY time DESC LIMIT 5"

# Node capacity and allocatable resources
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT node_name,
          capacity_cpu_cores,
          allocatable_cpu_cores,
          capacity_memory_bytes/1073741824 as total_memory_gb,
          allocatable_memory_bytes/1073741824 as allocatable_memory_gb
   FROM kubernetes_node
   ORDER BY time DESC LIMIT 1"

# Network traffic over time
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT derivative(mean(network_rx_bytes), 1s) as rx_bytes_per_sec,
          derivative(mean(network_tx_bytes), 1s) as tx_bytes_per_sec
   FROM kubernetes_node
   WHERE time > now() - 1h
   GROUP BY time(5m), node_name"

# Filesystem usage
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT node_name,
          fs_used_bytes/1073741824 as used_gb,
          fs_available_bytes/1073741824 as available_gb,
          (fs_used_bytes::float / (fs_used_bytes + fs_available_bytes)::float * 100) as used_percent
   FROM kubernetes_node
   ORDER BY time DESC LIMIT 5"
```

---

### 3. kubernetes_deployment

Deployment replica status.

**Fields:**
- `replicas_available` - Number of available replicas
- `replicas_unavailable` - Number of unavailable replicas
- `created` - Creation timestamp

**Tags:**
- `deployment_name` - Deployment name
- `namespace` - Namespace

**Example Queries:**

```bash
# Check all deployment statuses
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT deployment_name, namespace, replicas_available, replicas_unavailable
   FROM kubernetes_deployment
   ORDER BY time DESC LIMIT 20"

# Find deployments with unavailable replicas
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT deployment_name, namespace, replicas_unavailable
   FROM kubernetes_deployment
   WHERE replicas_unavailable > 0
   ORDER BY time DESC LIMIT 10"

# Monitor Airflow deployment availability
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT deployment_name, replicas_available
   FROM kubernetes_deployment
   WHERE deployment_name='airflow'
   ORDER BY time DESC LIMIT 10"
```

---

### 4. kubernetes_daemonset

DaemonSet status and replica counts.

**Tags:**
- `daemonset_name` - DaemonSet name
- `namespace` - Namespace

**Example Queries:**

```bash
# Check DaemonSet status
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_daemonset ORDER BY time DESC LIMIT 10"

# Monitor democratic-csi node DaemonSet
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_daemonset
   WHERE daemonset_name='democratic-csi-nvmeof-node'
   ORDER BY time DESC LIMIT 10"
```

---

### 5. kubernetes_statefulset

StatefulSet replica status.

**Tags:**
- `statefulset_name` - StatefulSet name
- `namespace` - Namespace

**Example Queries:**

```bash
# List all StatefulSets
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_statefulset ORDER BY time DESC LIMIT 10"
```

---

### 6. kubernetes_persistentvolume

Persistent volume phase tracking.

**Fields:**
- `phase_type` - PV phase (Bound, Available, Released, Failed)

**Tags:**
- `pv_name` - PersistentVolume name
- `storageclass` - Storage class name

**Example Queries:**

```bash
# Check PV status
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_persistentvolume ORDER BY time DESC LIMIT 10"

# Monitor NVMe-oF volumes
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_persistentvolume
   WHERE storageclass='truenas-nvmeof'
   ORDER BY time DESC LIMIT 10"
```

---

### 7. kubernetes_persistentvolumeclaim

PVC information and status.

**Tags:**
- `pvc_name` - PVC name
- `namespace` - Namespace
- `storageclass` - Storage class

**Example Queries:**

```bash
# List all PVCs
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_persistentvolumeclaim ORDER BY time DESC LIMIT 10"

# Check Airflow PVCs
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_persistentvolumeclaim
   WHERE namespace='automation'
   ORDER BY time DESC LIMIT 10"
```

---

### 8. kubernetes_pod_volume

Pod volume usage metrics.

**Fields:**
- `available_bytes` - Available space
- `capacity_bytes` - Total capacity
- `used_bytes` - Used space

**Tags:**
- `pod_name` - Pod name
- `namespace` - Namespace
- `volume_name` - Volume name

**Example Queries:**

```bash
# Check volume usage for all pods
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, volume_name,
          used_bytes/1073741824 as used_gb,
          capacity_bytes/1073741824 as capacity_gb,
          (used_bytes::float / capacity_bytes::float * 100) as used_percent
   FROM kubernetes_pod_volume
   WHERE capacity_bytes > 0
   ORDER BY time DESC LIMIT 10"

# Monitor InfluxDB volume usage
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, used_bytes/1073741824 as used_gb, capacity_bytes/1073741824 as capacity_gb
   FROM kubernetes_pod_volume
   WHERE pod_name =~ /influxdb/
   ORDER BY time DESC LIMIT 10"
```

---

### 9. kubernetes_pod_network

Pod network metrics.

**Fields:**
- `rx_bytes` - Bytes received
- `tx_bytes` - Bytes transmitted
- `rx_errors` - Receive errors
- `tx_errors` - Transmit errors

**Tags:**
- `pod_name` - Pod name
- `namespace` - Namespace

**Example Queries:**

```bash
# Check network usage
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, namespace, rx_bytes, tx_bytes
   FROM kubernetes_pod_network
   ORDER BY time DESC LIMIT 10"

# Calculate network rate over time
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT derivative(mean(rx_bytes), 1s) as rx_bytes_per_sec,
          derivative(mean(tx_bytes), 1s) as tx_bytes_per_sec
   FROM kubernetes_pod_network
   WHERE time > now() - 1h
   GROUP BY time(5m), pod_name, namespace"
```

---

### 10. kubernetes_service

Service information.

**Tags:**
- `service_name` - Service name
- `namespace` - Namespace

**Example Queries:**

```bash
# List all services
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT * FROM kubernetes_service ORDER BY time DESC LIMIT 10"
```

---

### 11. kubernetes_system_container

System container metrics (kubelet, runtime, etc.).

**Fields:**
- Similar to kubernetes_pod_container
- `cpu_usage_nanocores`
- `memory_working_set_bytes`
- etc.

**Tags:**
- `container_name` - System container name
- `node_name` - Node name

**Example Queries:**

```bash
# Monitor system containers
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT container_name, node_name,
          cpu_usage_nanocores/1000000 as cpu_millicores,
          memory_working_set_bytes/1048576 as memory_mb
   FROM kubernetes_system_container
   ORDER BY time DESC LIMIT 10"
```

---

## Common Monitoring Scenarios

### Scenario 1: Debug High CPU Usage

```bash
# Find top CPU consumers in last hour
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name,
          mean(cpu_usage_nanocores)/1000000 as avg_cpu_millicores
   FROM kubernetes_pod_container
   WHERE time > now() - 1h
   GROUP BY pod_name, container_name
   ORDER BY avg_cpu_millicores DESC
   LIMIT 10"
```

### Scenario 2: Memory Leak Detection

```bash
# Track memory growth over 24 hours
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name,
          first(memory_working_set_bytes)/1048576 as start_mb,
          last(memory_working_set_bytes)/1048576 as end_mb,
          (last(memory_working_set_bytes) - first(memory_working_set_bytes))/1048576 as growth_mb
   FROM kubernetes_pod_container
   WHERE time > now() - 24h
   GROUP BY pod_name, container_name"
```

### Scenario 3: Resource Quota Planning

```bash
# Compare requests vs actual usage
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name,
          resource_requests_millicpu_units as cpu_request,
          mean(cpu_usage_nanocores)/1000000 as avg_cpu_usage,
          resource_requests_memory_bytes/1048576 as memory_request_mb,
          mean(memory_working_set_bytes)/1048576 as avg_memory_mb
   FROM kubernetes_pod_container
   WHERE time > now() - 24h AND namespace='automation'
   GROUP BY pod_name, container_name, resource_requests_millicpu_units, resource_requests_memory_bytes"
```

### Scenario 4: Pod Restart Tracking

```bash
# Track restart events
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, container_name, restarts_total, state_reason
   FROM kubernetes_pod_container
   WHERE restarts_total > 0
   ORDER BY time DESC LIMIT 20"
```

### Scenario 5: Volume Space Monitoring

```bash
# Find volumes approaching capacity
kubectl exec -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf -execute \
  "SELECT pod_name, volume_name,
          used_bytes/1073741824 as used_gb,
          capacity_bytes/1073741824 as capacity_gb,
          (used_bytes::float / capacity_bytes::float * 100) as used_percent
   FROM kubernetes_pod_volume
   WHERE capacity_bytes > 0 AND (used_bytes::float / capacity_bytes::float) > 0.7
   ORDER BY used_percent DESC
   LIMIT 10"
```

---

## Interactive Shell Access

For ad-hoc queries, you can use the interactive InfluxDB shell:

```bash
kubectl exec -it -n storage influxdb-deployment-5bb7c6b99f-qn7nr -- influx -database telegraf
```

Then run queries directly:
```sql
SHOW MEASUREMENTS
SHOW TAG KEYS FROM kubernetes_pod_container
SHOW FIELD KEYS FROM kubernetes_pod_container
SELECT * FROM kubernetes_pod_container ORDER BY time DESC LIMIT 5
```

---

## Grafana Integration

These metrics are ideal for creating Grafana dashboards. Use the InfluxDB data source and reference measurements like:

```sql
SELECT mean("cpu_usage_nanocores")/1000000
FROM "kubernetes_pod_container"
WHERE ("namespace" = 'automation')
AND $timeFilter
GROUP BY time($__interval), "pod_name", "container_name" fill(null)
```

---

## Notes

- All CPU values are in nanocores. Divide by 1,000,000 for millicores.
- All memory values are in bytes. Divide by 1,048,576 for MB or 1,073,741,824 for GB.
- Timestamps are in nanoseconds since epoch.
- Use `now()` for relative time queries: `now() - 1h`, `now() - 24h`, etc.
- Use `GROUP BY time()` for time-series aggregations: `GROUP BY time(5m)`, `GROUP BY time(1h)`
