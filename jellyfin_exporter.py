import os
import sys
import time
import threading
import logging

import requests
from datetime import datetime, timedelta, timezone
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY

PORT = os.getenv('JELLYFIN_EXPORTER_PORT', 9027)
API_BASEURL = os.getenv('JELLYFIN_BASEURL', '')
API_KEY = os.getenv('JELLYFIN_APIKEY', '')

logging.basicConfig(format = '%(asctime)s %(levelname)s %(message)s',
                    level = logging.INFO,
                    datefmt = '%Y-%m-%d %H:%M:%S')

if API_BASEURL == '': 
    logging.error("JELLYFIN_BASEURL environment variable is required.")
    sys.exit(1)
if API_KEY == '':
    logging.error("JELLYFIN_APIKEY environment variable is required.")
    sys.exit(1)

logging.info("Starting jellyfin_exporter for '%s' on port: %d",
             str(API_BASEURL), PORT)

def request_api(action, p = {}):
    url = '{}{}'.format(API_BASEURL, action)
    params = p
    params["api_key"] = API_KEY
    start = time.time()
    data = requests.get(url, params).json()
    elapsed = time.time() - start
    logging.info("Request to %s (%s) returned in %s",
                url, p, elapsed)
    return data

class JellyfinCollector(object):
    def collect(self):
        try:
            sessions_data = request_api('/Sessions')

            sessions_count = 0
            sessions_count_active = 0
            streams_count = 0
            streams_direct_count = 0
            streams_transcode_count = 0

            metric_sessions = GaugeMetricFamily(
                'jellyfin_sessions',
                'Jellyfin user sessions',
                labels=['user', 'client', 'device_name', 'jellyfin_instance']
            )

            for user in sessions_data:
                if user['IsActive'] == True:
                    metric_sessions.add_metric(
                        [user['UserName'],
                         user['Client'],
                         user['DeviceName'],
                         API_BASEURL],
                         1
                    )
                    sessions_count += 1

                    last_active = datetime.fromisoformat(user["LastActivityDate"])
                    if last_active > datetime.now(timezone.utc) - timedelta(minutes=5):
                        sessions_count_active += 1

                if 'NowPlayingItem' in user:
                    streams_count += 1

                    now_playing = user['NowPlayingItem']
                    if 'TranscodingInfo' in now_playing:
                        tc = now_playing['TranscodingInfo']
                        if tc['IsVideoDirect'] == True:
                            streams_direct_count += 1
                        else:
                            streams_transcode_count += 1
                    else:
                        streams_direct_count += 1

            yield metric_sessions

            metric_sessions_count = GaugeMetricFamily(
                'jellyfin_sessions_count',
                'Jellyfin user sessions count',
                labels=['jellyfin_instance']
            )
            metric_sessions_count.add_metric([API_BASEURL], sessions_count)
            yield metric_sessions_count

            metric_sessions_count_active = GaugeMetricFamily(
                'jellyfin_sessions_count_active',
                'Jellyfin active user sessions count',
                labels=['jellyfin_instance']
            )
            metric_sessions_count_active.add_metric(
                [API_BASEURL], sessions_count_active)
            yield metric_sessions_count_active

            metric_streams = GaugeMetricFamily(
                'jellyfin_active_streams_count',
                'Jellyfin active streams count',
                labels=['jellyfin_instance']
            )
            metric_streams.add_metric([API_BASEURL], streams_count)
            yield metric_streams

            metric_streams_direct = GaugeMetricFamily(
                'jellyfin_active_streams_count_direct',
                'Jellyfin active streams count (direct)',
                labels=['jellyfin_instance']
            )
            metric_streams_direct.add_metric(
                [API_BASEURL], streams_direct_count)
            yield metric_streams_direct

            metric_streams_transcode = GaugeMetricFamily(
                'jellyfin_active_streams_count_transcode',
                'Jellyfin active streams count (transcode)',
                labels=['jellyfin_instance']
            )
            metric_streams_transcode.add_metric(
                [API_BASEURL], streams_transcode_count)
            yield metric_streams_transcode

            items_counts_data = request_api('/Items/Counts')

            metric_items_counts = GaugeMetricFamily(
                'jellyfin_item_counts',
                'Jellyfin items counts',
                labels=['type', 'jellyfin_instance']
            )
            for metric, val in items_counts_data.items():
                metric_items_counts.add_metric([metric, API_BASEURL], val)
            yield metric_items_counts

        except Exception as ex:
            logging.error('Error getting metrics: %s', ex)

REGISTRY.register(JellyfinCollector())
start_http_server(PORT)

e = threading.Event()
e.wait()
