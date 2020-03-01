#!/bin/bash
# Create playlist using the Grafana API

url=localhost:3000
playlist=/etc/grafana/provisioning/playlists/playlists.json
user=$GF_SECURITY_ADMIN_USER
password=$GF_SECURITY_ADMIN_PASSWORD

initialised=false;

while [[ $initialised == false ]];
do
echo "Initiallising...";
var=$(curl --write-out %{http_code} --silent --output /dev/null http://${url}/api/playlists);

if [[ "$var" == "200" ]]; then
    if [[ $(curl --write-out %{http_code} --silent --output /dev/null http://${url}/api/playlists/1) == "200" ]]; then
        echo "Playlist created."
    else
        echo "Creating playlists..."
        curl -s -X POST -H "content-type: application/json" -u ${user}:${password} -d @${playlist} http://${url}/api/playlists
    fi
    initialised=true
else
    echo $var
    sleep 5
fi
done
