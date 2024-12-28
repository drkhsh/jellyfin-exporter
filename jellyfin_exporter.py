#!/usr/bin/env python3
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
                labels=['user', 'client', 'device_name', 'last_active',
                        'jellyfin_instance']
            )

            metric_streams = GaugeMetricFamily(
                'jellyfin_streams',
                'Jellyfin user streams',
                labels=['user', 'client', 'device_name', 'play_name', 'path',
                        'run_time_ticks', 'container', 'video_display_title',
                        'bit_rate', 'bit_depth', 'color_space',
                        'audio_display_title', "is_paused",
                        "is_muted", "volume_level", "play_method",
                        'jellyfin_instance']
            )

            for user in sessions_data:
                now_playing_name = ""
                path = ""
                run_time_ticks = 0
                container = ""
                video_display_title = ""
                bit_rate = 0
                bit_depth = 0
                color_space = ""
                audio_display_title = ""
                play_state = user.get("PlayState", None)
                playing_position_ms = 0
                is_paused = False
                is_muted = False
                volume_level = 0
                play_method = ""

                if user.get("UserName", None) is None:
                    continue

                sessions_count += 1

                if 'NowPlayingItem' in user:
                    streams_count += 1

                    now_playing = user['NowPlayingItem']
                    if 'TranscodingInfo' in user:
                        tc = user['TranscodingInfo']
                        if tc['IsVideoDirect'] == True:
                            streams_direct_count += 1
                        else:
                            streams_transcode_count += 1
                    else:
                        streams_direct_count += 1

                    now_playing_name = now_playing.get("Name", "")
                    path = now_playing.get("Path", "")
                    run_time_ticks = now_playing.get("RunTimeTicks", 0)
                    container = now_playing.get("Container", "")
                    if len(now_playing.get("MediaStreams", [])) > 1:
                        video_display_title = now_playing.get("MediaStreams", [])[0].get("DisplayTitle", "")
                        bit_rate = now_playing.get("MediaStreams", [])[0].get("BitRate", 0)
                        bit_depth = now_playing.get("MediaStreams", [])[0].get("BitDepth", 0)
                        color_space = now_playing.get("MediaStreams", [])[0].get("ColorSpace", "")
                        audio_display_title = now_playing.get("MediaStreams", [])[1].get("DisplayTitle", "")

                    play_state = user.get("PlayState", None)
                    if play_state is not None:
                        playing_position_ms = play_state.get("PositionTicks", 0)
                        is_paused = play_state.get("IsPaused", False)
                        is_muted = play_state.get("IsMuted", False)
                        volume_level = play_state.get("VolumeLevel", 0)
                        play_method = play_state.get("PlayMethod", "")

                    metric_streams.add_metric(
                        [user['UserName'],
                         user['Client'],
                         user['DeviceName'],
                         now_playing_name,
                         path,
                         str(run_time_ticks),
                         container,
                         video_display_title,
                         str(bit_rate),
                         str(bit_depth),
                         color_space,
                         audio_display_title,
                         str(playing_position_ms),
                         str(is_paused),
                         str(is_muted),
                         str(volume_level),
                         play_method,
                         API_BASEURL],
                         1
                    )

                if user['IsActive'] == True:
                    last_active = datetime.fromisoformat(user["LastActivityDate"])
                    if last_active > datetime.now(timezone.utc) - timedelta(minutes=60):
                        sessions_count_active += 1

                        metric_sessions.add_metric(
                            [user['UserName'],
                             user['Client'],
                             user['DeviceName'],
                             user["LastActivityDate"],
                             API_BASEURL],
                             1
                        )

            yield metric_streams
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

            users_data = request_api('/Users')
            users_data_disabled = request_api('/Users', {
                "isDisabled": True
            })

            users_count = 0
            users_count_disabled = 0

            for user in users_data:
                users_count += 1
            for user in users_data_disabled:
                users_count_disabled += 1

            metric_users_count = GaugeMetricFamily(
                'jellyfin_users_count',
                'Jellyfin users count',
                labels=['jellyfin_instance']
            )
            metric_users_count.add_metric([API_BASEURL], users_count)
            yield metric_users_count

            metric_users_count_disabled = GaugeMetricFamily(
                'jellyfin_users_count_disabled',
                'Jellyfin users count',
                labels=['jellyfin_instance']
            )
            metric_users_count_disabled.add_metric([API_BASEURL], users_count_disabled)
            yield metric_users_count_disabled

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
