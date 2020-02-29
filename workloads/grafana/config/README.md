# Build instructions

    kubectl create configmap grafana-config -n grafana --dry-run --from-file=dashboards.yaml=dashboards.yaml --from-file=grafana.ini=grafana.ini --from-file=playlists.json=playlists.json -o yaml > grafana-config.yaml