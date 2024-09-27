# jellyfin-exporter

This is a Prometheus (https://prometheus.io) metrics exporter for Jellyfin
(https://jellyfin.org).

## Configuration

This exporter is configured via environment variables:

- `JELLYFIN_BASEURL`: Jellyfin server address (**required**)
- `JELLYFIN_APIKEY`: Jellyfin API key (**required**)
- `JELLYFIN_EXPORTER_PORT`: The port on which the exporter listens
  (default `9027`)

## Running

### Using docker

```
$ docker run \
   -e JELLYFIN_BASEURL=http(s)://<jellyfin address>:<port> \
   -e JELLYFIN_APIKEY=<apikey> \
   -p 9027:9027 \
   -d --restart=always \
   -n jellyfin_exporter \
   drkhsh/jellyfin-exporter:dev
```

### Using docker-compose

See [docker-compose file](docker-compose.yml).

### Using package manager

Install dependencies, e.g. using:

```
# apt install python3-prometheus-client
```

### Manually

1. Create a new python virtual environment: `python3 -m venv .venv`
2. Install required modules into your venv:
   `./.venv/bin/pip3 install -r requirements.txt`
3. Start the exporter:

```
JELLYFIN_BASEURL=http://<jellyfin address>:<port> JELLYFIN_APIKEY=<apikey> \
	./.venv/bin/python3 jellyfin_exporter.py
```

### systemd service

see `jellyfin-exporter.service` in *contrib* directory.
change the environment vars accordingly in a service override

## Exported Metrics

Common labels:
  - jellyfin_instance (`JELLYFIN_BASEURL`)

General metrics:
- jellyfin_sessions
- jellyfin_sessions_count
- jellyfin_sessions_count_active
- jellyfin_active_streams_count
- jellyfin_active_streams_count_direct
- jellyfin_active_streams_count_transcode
- jellyfin_item_counts
