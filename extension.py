from ulauncher.api.client.Extension import Extension # noqa
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent, SystemExitEvent # noqa
from ulauncher.api.client.EventListener import EventListener # noqa
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem # noqa
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem # noqa
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction # noqa
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction # noqa
from ulauncher.api.shared.action.BaseAction import BaseAction # noqa
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction # noqa
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction # noqa
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction # noqa

import time
import os
import logging
import random
import shutil
from urllib.parse import urlparse
from typing import Union

import spotipy
from spotipy.oauth2 import SpotifyPKCE
import requests


logger = logging.getLogger(__name__)


class UlauncherSpotifyAPIExtension(Extension, EventListener):

    CLIENT_ID = '1f3a663c5fdd4056b4c0e122ea55a3af'
    SCOPES = 'user-modify-playback-state user-read-playback-state'
    CACHE_FOLDER = os.path.join(os.path.dirname(__file__), 'cache')
    ACCESS_TOKEN_CACHE = os.path.join(os.path.dirname(__file__), 'cache.json')
    REDIRECT_URI = 'http://127.0.0.1:8080' # TODO preferences modify port

    def __init__(self):
        super(UlauncherSpotifyAPIExtension, self).__init__()

        # even though it might be a good idea to separate extension logic thoroughly
        # there's no added benefit for such a small project
        # so instead of using proper listener, handle the events here
        self.subscribe(KeywordQueryEvent, self)
        self.subscribe(ItemEnterEvent, self)
        self.subscribe(SystemExitEvent, self)

        # icons
        self.icons = {
            'main': os.path.join(os.path.dirname(__file__), 'images/icon.png'),
            'notification': os.path.join(os.path.dirname(__file__), 'images/icon_black.png'),
            'play': os.path.join(os.path.dirname(__file__), 'images/play.png'),
            'pause': os.path.join(os.path.dirname(__file__), 'images/pause.png'),
            'next': os.path.join(os.path.dirname(__file__), 'images/next.png'),
            'prev': os.path.join(os.path.dirname(__file__), 'images/prev.png'),
            'repeat_off': os.path.join(os.path.dirname(__file__), 'images/repeat_off.png'),
            'repeat_context': os.path.join(os.path.dirname(__file__), 'images/repeat_context.png'),
            'repeat_track': os.path.join(os.path.dirname(__file__), 'images/repeat_track.png'),
            'shuffle': os.path.join(os.path.dirname(__file__), 'images/shuffle_on.png'),
            'no_shuffle': os.path.join(os.path.dirname(__file__), 'images/shuffle_off.png')
        }

        # create cache folder
        # TODO preferences checkbox clear cache after exit
        if not os.path.exists(self.CACHE_FOLDER):
            os.mkdir(self.CACHE_FOLDER)

        # aliases
        # TODO preferences modify aliases
        self.aliases = {
            's': 'search',
            'song': 'track'
        }

        # spotipy - spotify api client
        auth = SpotifyPKCE(client_id=self.CLIENT_ID,
                           redirect_uri=self.REDIRECT_URI,
                           scope=self.SCOPES,
                           cache_path=self.ACCESS_TOKEN_CACHE)
        self.api = spotipy.Spotify(auth_manager=auth)

    def _clear_cache(self) -> None:
        shutil.rmtree(self.CACHE_FOLDER, ignore_errors=True)
        return

    # download image to cache and return path to the cached image
    def _dl_image(self, url: str) -> str:
        filename = os.path.basename(urlparse(url).path)
        cache_path = os.path.join(self.CACHE_FOLDER, filename)

        if os.path.exists(cache_path):
            return cache_path
        else:
            img = requests.get(url, stream=True)
            with open(cache_path, 'wb') as f:
                shutil.copyfileobj(img.raw, f)

        return cache_path

    # helper for humanizing duration in ms
    def _parse_duration(self, ms: int, short: bool = False) -> str:
        hours, ms = divmod(ms, 3600000)
        minutes, ms = divmod(ms, 60000)
        seconds = float(ms) / 1000

        if short:
            if hours:
                return f'{hours:.0f}:{minutes:.0f}:{seconds:2.0f}'
            if minutes:
                return f'{minutes:.0f}:{seconds:2.0f}'
            if seconds:
                return f'{seconds:2.0f}'
        else:
            duration = ''
            if hours:
                duration += f'{hours:.0f}h'
            if minutes:
                duration += f' {minutes:.0f}m'
            if seconds:
                duration += f' {seconds:.0f}s'
            return duration

    # a wrapper helper to generate an item
    def _generate_item(self, title: str = '', desc: str = '', icon: str = '', small: bool = False,
                       action: Union[dict, BaseAction] = DoNothingAction(),
                       alt_action: Union[dict, BaseAction] = DoNothingAction(),
                       keep_open: bool = False) -> Union[ExtensionResultItem, ExtensionSmallResultItem]:

        if isinstance(action, dict):
            action['_keep_app_open'] = keep_open
            action = ExtensionCustomAction(action, keep_app_open=keep_open)
        if isinstance(alt_action, dict):
            alt_action['_keep_app_open'] = keep_open
            alt_action = ExtensionCustomAction(alt_action, keep_app_open=keep_open)

        if small:
            item = ExtensionSmallResultItem
        else:
            item = ExtensionResultItem

        return item(name=title.replace('&', '&#38;') if title else '',
                    description=desc.replace('&', '&#38;') if desc else '',
                    icon=icon if icon else self.icons['main'],
                    on_enter=action if action else DoNothingAction(),
                    on_alt_enter=alt_action if alt_action else DoNothingAction())

    # helper for the currently playing entries
    def _generate_now_playing_menu(self, currently_playing: dict = None,
                                   next: bool = True, prev: bool = True):

        if not currently_playing:
            currently_playing = self.api.current_playback()

        if not currently_playing or not currently_playing['item']:
            return None

        artists = ', '.join([artist['name'] for artist in currently_playing['item']['artists']])
        song_name = currently_playing['item']['name']
        album_name = currently_playing['item']['album']['name']
        device_playing_on_type = currently_playing['device']['type'].lower()
        device_playing_on_name = currently_playing['device']['name']
        is_playing = currently_playing['is_playing']
        status = 'Playing' if is_playing else 'Paused'
        track_progress = self._parse_duration(currently_playing['progress_ms'], short=True)
        track_duration = self._parse_duration(currently_playing['item']['duration_ms'], short=True)

        items = [self._generate_item(f'{artists} -- {song_name}',
                                     f'Album: {album_name} | '
                                     f'{status} on: {device_playing_on_type} {device_playing_on_name} | '
                                     f'{track_progress}/{track_duration}',
                                     self.icons['pause'] if is_playing else self.icons['play'],
                                     action={'command': 'pause' if is_playing else 'play'},
                                     keep_open=True if not is_playing else False)]

        if next:
            items.append(self._generate_item('Next track',
                                             'Skip playback to next track',
                                             self.icons['next'],
                                             action={'command': 'next'},
                                             keep_open=True))

        if prev:
            items.append(self._generate_item('Previous track',
                                             'Skip playback to previous track',
                                             self.icons['prev'],
                                             action={'command': 'prev'},
                                             keep_open=True))
        return items

    # another helper to render items or a single item
    def _render(self, i: Union[list, ExtensionResultItem]) -> RenderResultListAction:
        if isinstance(i, list):
            return RenderResultListAction(i)
        elif isinstance(i, ExtensionResultItem):
            return RenderResultListAction([i])

    # distribute events to proper listeners
    def on_event(self, event, extension):
        if extension is not self:
            raise RuntimeError('Something is very wrong.')
        if isinstance(event, KeywordQueryEvent):
            return self.on_keyword_query(event.get_keyword(), event.get_argument())
        if isinstance(event, ItemEnterEvent):
            return self.on_item_enter(event.get_data())
        if isinstance(event, SystemExitEvent):
            return self.on_system_exit()

    def on_system_exit(self):
        logger.debug(f'Received system exit event, clearing image cache')
        return self._clear_cache()
        pass

    def on_keyword_query(self, keyword: str, argument: str):

        # if user is not authorized or no cached token => go through authorization flow and get the tokens
        if self.api.auth_manager.get_cached_token() is None:
            return self._render(self._generate_item(title='Authorization',
                                                    desc='Authorize the extension with your Spotify account',
                                                    action={'command': 'auth'}))

        # if user has a query => process the query
        if argument:
            command, *components = argument.split()
            logger.debug(f'Recognized query "{argument}", split into command "{command}" and components "{components}"')

            if command in self.aliases:
                logger.debug(f'Command {command} is an alias for {self.aliases[command]}')
                command = self.aliases[command]

            if command == 'switch':
                logger.debug(f'Playback transfer')

                user_devices = self.api.devices()
                if user_devices.get('devices', None):
                    items = []
                    for device in user_devices['devices']:
                        device_name = device.get('name', 'device_name')
                        device_id = device.get('id', 'device_id')
                        device_type = device.get('type', 'device_type').lower()
                        current = 'Current device | ' if device.get('is_active') else ''

                        items.append(self._generate_item(title=f'Switch playback to {device_type} {device_name}',
                                                         desc=f'{current}Device id: {device_id}',
                                                         icon=self.icons['play'],
                                                         action={'command': 'switch',
                                                                 'device_id': device_id}))
                    return self._render(items)
                else:
                    return self._render(self._generate_item(title='No active devices running Spotify found',
                                                            desc='Open Spotify on one of your devices first',
                                                            action=HideWindowAction()))

            elif command in ['album', 'track', 'artist', 'playlist', 'search']:
                logger.debug(f'Searching')

                if len(components) == 0:
                    examples = {
                        'album': ['sp album mick gordon doom', 'sp album beach house bloom',
                                  'sp album foals holy fire'],
                        'artist': ['sp artist spice girls', 'sp artist britney spears', 'sp artist jakey'],
                        'track': ['sp track led zep no quarter', 'sp track post malone congratulations',
                                  'sp track post malone wow'],
                        'playlist': ['sp playlist brain food', 'sp playlist russian hardbass',
                                     'sp playlist spanish flamenco'],
                        'search': ['sp search bad guy', 'sp search gojira', 'sp search bonobo']
                    }
                    if command != 'search':
                        search_for = f'Search for {command}s'
                    else:
                        search_for = f'Enter your search query'
                    return self._render(self._generate_item(f'{search_for}',
                                                            f'For example: {random.choice(examples[command])}',
                                                            icon=self.icons['main'],
                                                            action=DoNothingAction()))

                if command == 'search':
                    type_search = 'album,track,artist,playlist'
                    # TODO preferences make query limit customizable
                    limit = 2
                else:
                    type_search = command
                    # TODO preferences make query limit customizable
                    limit = 7

                query = ' '.join(components)
                search_results = self.api.search(query, limit=limit, type=type_search)
                if not search_results:
                    return self._render(self._generate_item(f'Nothing found for {query}',
                                                            f'Try again with different query?',
                                                            action=DoNothingAction()))

                items = []
                results = [item for i in search_results for item in search_results[i]['items']]

                for res in results:
                    category = res['type']
                    context_or_track_uri = 'uris' if category == 'track' else 'context_uri'
                    uri = res['uri']
                    alt_action = DoNothingAction()

                    if category == 'album':
                        artists = ', '.join([artist['name'] for artist in res['artists']])
                        name = res['name']
                        n_tracks = res['total_tracks']
                        released = res['release_date']
                        if 'images' in res and res['images']:
                            smallest_img = min(res['images'], key=lambda x: x['height'])
                            img = self._dl_image(smallest_img['url'])
                        else:
                            img = self.icons['main']

                        title = f'{artists} -- {name}'
                        desc = f'Album | {n_tracks} tracks | Released {released}'

                    elif category == 'artist':
                        name = res['name']
                        popularity = res['popularity']
                        genres = ', '.join(res['genres']).capitalize()
                        genres_output = f' | {genres}' if genres else ''
                        if 'images' in res and res['images']:
                            smallest_img = min(res['images'], key=lambda x: x['height'])
                            img = self._dl_image(smallest_img['url'])
                        else:
                            img = self.icons['main']

                        title = f'{name}'
                        desc = f'Artist{genres_output} | Popularity {popularity}%'

                    elif category == 'track':
                        artists = res['artists'][0]['name']
                        name = res['name']
                        album_name = res['album']['name']
                        popularity = res['popularity']
                        duration = self._parse_duration(res['duration_ms'])
                        if 'images' in res['album'] and res['album']['images']:
                            smallest_img = min(res['album']['images'], key=lambda x: x['height'])
                            img = self._dl_image(smallest_img['url'])
                        else:
                            img = self.icons['main']

                        title = f'{artists} -- {name}'
                        desc = f'Track | {duration} | Popularity {popularity}% | {album_name}'
                        alt_action = {'command': 'queue', 'uri': uri}
                        uri = [uri]

                    elif category == 'playlist':
                        name = res['name']
                        description = f' | {res["description"]}' if res['description'] else ''
                        owner = res['owner']['display_name']
                        n_tracks = res['tracks']['total']
                        if 'images' in res and res['images']:
                            img = self._dl_image(res['images'][0]['url'])
                        else:
                            img = self.icons['main']

                        title = f'{name}'
                        desc = f'Playlist by {owner} | {n_tracks} tracks{description}'
                    else:
                        raise RuntimeError('Wrong category received from Spotify api?')

                    items.append(self._generate_item(title, desc, img,
                                                     action={'command': 'play',
                                                             context_or_track_uri: uri},
                                                     alt_action=alt_action,
                                                     keep_open=False))

                return self._render(items)

            elif command == 'repeat':
                logger.debug(f'Playback repeat status')

                currently_playing = self.api.current_playback()
                if not currently_playing or not currently_playing['item']:
                    return self._render(self._generate_item('Nothing is playing at this moment',
                                                            'Start playing first',
                                                            action=HideWindowAction()))

                states = ['off', 'context', 'track']
                state_names = ['do not repeat', 'repeat context', 'repeat track']
                current_repeat_state: str = currently_playing.get('repeat_state')
                current_repeat_state_index = states.index(current_repeat_state)

                items = [self._generate_item(f'Current state: {state_names[current_repeat_state_index]}',
                                             small=True, icon=self.icons[f'repeat_{current_repeat_state}'],
                                             action=DoNothingAction())]

                for i in range(len(states)):
                    if i == current_repeat_state_index:
                        continue
                    items.append(self._generate_item(f'Set to {state_names[i]}',
                                                     small=True, icon=self.icons[f'repeat_{states[i]}'],
                                                     action={'command': 'repeat',
                                                             'state': states[i]},
                                                     keep_open=False))
                return self._render(items)

            elif command == 'shuffle':
                logger.debug(f'Playback shuffle status')

                currently_playing = self.api.current_playback()
                if not currently_playing or not currently_playing['item']:
                    return self._render(self._generate_item('Nothing is playing at this moment',
                                                            'Start playing first',
                                                            action=HideWindowAction()))

                current_shuffle_state = currently_playing.get('shuffle_state')
                states = [True, False]
                state_names = ['shuffle', 'do not shuffle']
                state_icons = ['shuffle', 'no_shuffle']
                current_shuffle_state_index = states.index(current_shuffle_state)

                items = [self._generate_item(f'Current state: {state_names[current_shuffle_state_index]}',
                                             small=True, icon=self.icons[state_icons[current_shuffle_state_index]],
                                             action=DoNothingAction())]

                for i in range(len(states)):
                    if i == current_shuffle_state_index:
                        continue
                    items.append(self._generate_item(f'Set to {state_names[i]}',
                                                     small=True, icon=self.icons[state_icons[i]],
                                                     action={'command': 'shuffle',
                                                             'state': states[i]},
                                                     keep_open=False))
                return self._render(items)

        # no query, but something is playing currently => show now playing menu
        current_playback = self.api.current_playback()
        if current_playback:
            return self._render(self._generate_now_playing_menu(current_playback))

        # no query, nothing is playing, but there are devices online => offer user to start playback on one of them
        user_devices = self.api.devices()
        if user_devices.get('devices', None):
            items = []
            for device in user_devices['devices']:
                device_name = device.get('name', 'device_name')
                device_id = device.get('id', 'device_id')
                device_type = device.get('type', 'device_type').lower()

                items.append(self._generate_item(f'Start playback on {device_type} {device_name}',
                                                 f'Device id: {device_id}',
                                                 self.icons['play'],
                                                 action={'command': 'play',
                                                         'device_id': device_id},
                                                 keep_open=True))

            return self._render(items)

        # no query, nothing is playing, no devices online => prompt to open Spotify anywhere first
        return self._render(self._generate_item('No active devices running Spotify found',
                                                'Open Spotify on one of your devices first',
                                                action=HideWindowAction()))

    def on_item_enter(self, data: dict):
        command = data.get('command', '')
        keep_open = data.get('_keep_app_open', False)
        logger.debug(f'Received command {command} ({data})')

        try:
            if command == 'auth':
                try:
                    self.api.auth_manager.get_access_token()
                    return
                except spotipy.SpotifyOauthError as e:
                    logger.debug(f'Could not authenticate', e)
                    return

            elif command == 'pause':
                logger.debug(f'Pausing...')
                self.api.pause_playback()

            elif command == 'play':
                device_id = data.get('device_id', None)
                context_uri = data.get('context_uri', None)
                uris = data.get('uris', [])
                if uris:
                    logger.debug(f'Playing (device_id: {device_id}, uris: {uris})...')
                    self.api.start_playback(device_id=device_id, uris=uris)
                elif context_uri:
                    logger.debug(f'Playing (device_id: {device_id}, context_uri: {context_uri}...')
                    self.api.start_playback(device_id=device_id, context_uri=context_uri)
                else:
                    logger.debug(f'Playing (device_id: {device_id})...')
                    self.api.start_playback(device_id=device_id)

            elif command == 'queue':
                uri = data.get('uri', None)
                logger.debug(f'Adding {uri} to queue...')
                self.api.add_to_queue(uri)

            elif command == 'next':
                logger.debug(f'Skipping to next...')
                self.api.next_track()

            elif command == 'prev':
                logger.debug(f'Skipping to previous...')
                self.api.previous_track()

            elif command == 'switch':
                logger.debug(f'Switching device...')
                self.api.transfer_playback(device_id=data.get('device_id', None))

            elif command == 'shuffle':
                state = data.get('state', False)
                logger.debug(f'Setting shuffle to {state}')
                self.api.shuffle(state)

            elif command == 'repeat':
                state = data.get('state', 'off')
                logger.debug(f'Setting repeat to {state}')
                self.api.repeat(state)

            else:
                logger.debug('No handler for this command...')
                return self._render(self._generate_item('Empty or unknown command',
                                                        'Please investigate or open a github issue!',
                                                        action=HideWindowAction()))

            if keep_open:
                # very ugly hack :(
                time.sleep(0.5)
                # Spotify api is asynchronous and without this,
                # there might be a discrepancy in what's currently playing.
                # For example, you press next, the request to skip is sent and successfully acknowledged (http 204)
                # but what's currently playing depends on client and it still hasn't changed.
                # This ugly hack will minimize the possibility of that happening, but probably not completely.
                # There must be a better way.
                return self._render(self._generate_now_playing_menu())
            else:
                return

        except spotipy.SpotifyException as e:
            logger.debug(f'Received an exception, {e}')

            if e.http_status == 403:
                return self._render(self._generate_item('Spotify: 403 Forbidden',
                                                        'Forbidden to access this endpoint'
                                                        'or state has changed',
                                                        action=HideWindowAction()))

            elif e.http_status == 401:
                return self._render(self._generate_item('Spotify: 401 Unauthorized',
                                                        'Probably, scope of the request is not authorized',
                                                        action=HideWindowAction()))

            elif e.http_status == 404:
                return self._render(self._generate_item('Spotify: 404 Not Found',
                                                        'Probably, request is not complete and missing something',
                                                        action=HideWindowAction()))

            elif e.http_status in self.api.default_retry_codes:
                return self._render(self._generate_item(f'Spotify: {e.http_status}',
                                                        'Spotify asks to try again later',
                                                        action=HideWindowAction()))
            else:
                logger.debug('Unknown SpotifyException', e)
                return self._render(self._generate_item(f'Spotify exception: {e.http_status}',
                                                        f'Code: {e.code}, msg: {e.msg}',
                                                        action=HideWindowAction()))
