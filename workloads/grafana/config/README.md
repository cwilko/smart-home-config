# Build instructions

    kubectl create configmap grafana-config -n grafana --dry-run --from-file=dashboards.yaml=dashboards.yaml --from-file=grafana.ini=grafana.ini --from-file=playlists.json=playlists.json --from-file=loki-datasource.yaml=loki-datasource.yaml -o yaml > grafana-config.yaml