from actions import *
from preferredsoundplayer import *
from torch.backends.cuda import cuBLASModule
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

from echo import ttsEcho
from tts_websocket import ttsWebsocket

import asyncio
import configparser
import glob
import json
import os
import queue
import re
import requests
import shutil
import torch.multiprocessing as mp
import websocket
import websockets

DEVMODE = False

# Workers
def gen_worker(gen_queue, generate):
    while True:
        try:
            generate(gen_queue.get(timeout=1))
        except (queue.Empty, IndexError):
            continue

def tts_worker(tts_queue, play_audio):
    while True:
        try:
            play_audio(tts_queue.get(timeout=1))
        except (queue.Empty, IndexError):
            continue

class ttsController:
    USER_SCOPE = [
        AuthScope.BITS_READ,
        AuthScope.CHANNEL_MODERATE,
        AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
        AuthScope.USER_READ_CHAT
    ]
    URI = 'https://api.twitch.tv/helix'
    WS_ENDPOINT = 'wss://eventsub.wss.twitch.tv/ws' if not DEVMODE else 'ws://127.0.0.1:8080/ws'
    SUBS_ENDPOINT = 'https://api.twitch.tv/helix/eventsub/subscriptions' if not DEVMODE else 'http://127.0.0.1:8080/eventsub/subscriptions'
    SUBSCRIPTIONS = [
        'channel.subscription.message',
        'channel.subscription.gift',
        'channel.cheer',
        'channel.chat.message'
    ]

    def __init__(self):
        # config
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        # twitch auth stuff
        self.token = None
        self.refresh_token = None
        self.headers = {}
        self.subscriptions = []
        self.broadcaster = {}
        self.ws_app = None

        # queues and processs for background work
        mp.set_start_method('spawn', force=True)
        self.gen_queue = mp.Queue()
        self.tts_queue = mp.Queue()
        self.gen_worker_process = mp.Process(target=gen_worker, args=(self.gen_queue, self.generate,), daemon=True)
        self.tts_worker_process = mp.Process(target=tts_worker, args=(self.tts_queue, self.play_audio,), daemon=True)
        self.gen_worker_process.start()
        self.tts_worker_process.start()

        # visual details for frontend
        self.tts_text = []
        self.currently_playing = None
        self.speaker_list = eval(self.config['AI']['speakers'])
        self.sound_list = eval(self.config['SOUND']['sounds'])
        self.connected = False

        # ai controller
        self.echo = ttsEcho(self)

        # actions
        self.actions = {
            'SESSION': sessionStartAction(self, self.config, 'SESSION'),
            'AI': aiAction(self, self.config, 'AI'),
            'CHAT': chatAction(self, self.config, 'CHAT'),
            'LUTE': luteAction(self, self.config, 'LUTE'),
            'SOUND': soundAction(self, self.config, 'SOUND'),
            'TTS': ttsAction(self, self.config, 'TTS'),
        }

        # websocket server
        self.current_speaker = "none"
        #self.websocket_server = ttsWebsocket(self)
        #def run_server():
        #    ayncio.run(self.websocket_server.start())
        #self.websocket_process = mp.Process(target=run_server, daemon=True)

    # Config
    def save_config(self):
        print("Saving config")
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)

    # Shutdown
    def shutdown(self):
        self.save_config()
        while not self.gen_queue.empty():
            try:
                self.gen_queue.get(block=False)
                self.gen_queue.task_done()
            except mp.Queue.Empty:
                break

        while not self.tts_queue.empty():
            try:
                self.tts_queue.get(block=False)
                self.tts_queue.task_done()
            except mp.Queue.Empty:
                break

        #self.websocket_server.stop()
        self.echo.unload_models()

        print("Shutting down")

    # Generator
    def generate(self, message_list):
        audio_list = []
        for msg in message_list:
            try:
                msg_obj = self.actions[msg['type']].generate(msg)
                if bool(msg_obj):
                    audio_list.append(msg_obj)
            except Exception as e:
                print(f'Failed to generate audio, aborting message: {e}')
                break

        if len(audio_list) > 0:
            self.tts_queue.put(audio_list)
        self.gen_process.task_done()
        return

    # File player
    def play_audio(self, audio_list):
        self.current_speaker = "none"
        soundplay("assets/cheer.wav", block=True)
        sleep(0.25)
        media_paused = False
        session = None
        for msg_obj in audio_list:
            if 'filename' not in list(msg_obj): continue

            if msg_obj['type'] == 'LUTE' and self.config['LUTE'].getboolean('pause_music'):
                session = asyncio.run(get_media_session())
                if session is not None:
                    media_paused = session.get_playback_info().playback_status.value == 4
                    session.try_pause_async()

            try:
                sound_muted = not self.config[msg_obj['type']].getboolean('active')

                if msg_obj['type'] not in self.sound_list.keys() and not sound_muted:
                    self.current_speaker = msg_obj['type']
                    sleep(0.5)

                if not sound_muted:
                    self.currently_playing = soundplay(msg_obj['filename'])
                    while getIsPlaying(self.currently_playing):
                        if self.config['FLAGS'].getboolean('clear') or self.config['FLAGS'].getboolean('skip'):
                            stopsound(self.currently_playing)
                            self.config.set('FLAGS', 'skip', str(False))
                        sleep(0.1)

                    stopsound(self.currently_playing)

                self.current_speaker = 'none' if not self.config['FLAGS'].getboolean('pause') else 'paused'
                os.remove(msg_obj['filename'])
            except:
                print(f'Could not play file.')

            if session is not None and media_paused:
                session.try_play_async()
                media_paused = False

        # Hack way to let GUI know to decrease the visible messages?
        self.currently_playing = None
        self.tts_queue.task_done()

        # Remove from out text
        self.tts_text = self.tts_text[1:]
        return

    # Twitch WebSocket event methods
    def on_open(self, ws):
        # update the color
        self.connected = True
        print('Connected to Twitch')

    def on_message(self, ws, msg):
        msg = json.loads(msg)

        try:
            if msg['metadata']['message_type'] == 'session_welcome':
                self.actions['SESSION'].action(msg)

            if msg['metadata']['message_type'] != 'notification': return

            message_list = []
            message = msg['payload']['event']['message']
            if type(message) == dict:
                message = message['text']

            message_parts = message.split()
            last_action = None
            last_key = None
            last_ind = 0

            for i, sub_message in enumerate(message_parts):
                if len(sub_message.strip()) == 0: continue

                for action in self.actions.values():
                    key = action.validate(msg, sub_message)
                    if bool(key):
                        if last_action is None: last_action = action
                        if last_key is None: last_key = key

                        if last_action != action or (last_key != key and key != action.default_value) or key[0] == self.config['DEFAULT']['split_text']:
                            msg['sub_message'] = ' '.join(message_parts[last_ind:i])
                            msg_obj = last_action.action(msg)
                            if bool(msg_obj):
                                message_list.append(msg_obj)

                            last_action = action
                            last_key = key
                            last_ind = i
                            break

            # final section of message
            if bool(last_action):
                msg['sub_message'] = ' '.join(message_parts[last_ind:])
                msg_obj = last_action.action(msg)
                if bool(msg_obj):
                    message_list.append(msg_obj)

            if len(message_list) > 0:
                self.tts_text.append({
                    'user_name': msg['payload']['event']['user_name'],
                    'message': message
                })

            self.gen_queue.put(message_list)
        except Exception as e:
            print(f'Unable to handle inbound WS message: {e}')

                
    def on_error(self, ws, msg):
        print(f'An error has occurred: {msg}')
        return

    def on_close(self, ws, close_status_code, msg):
        self.connected = False
        print('Closed')
        return

    #Authentication
    async def update_stored_creds(self, token, refresh):
        print("Access token refreshed successfully")
        with open(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json"), 'w') as f:
            json.dump({'token': token, 'refresh': refresh}, f)

    async def auth(self):
        # Just use pre-built twitch auth
        if bool(self.config['DEFAULT']['TwitchAppId']) and bool(self.config['DEFAULT']['TwitchAppSecret']):
            twitch = await Twitch(self.config['DEFAULT']['TwitchAppId'], self.config['DEFAULT']['TwitchAppSecret'])

            auth = UserAuthenticator(twitch, ttsController.USER_SCOPE)
            self.token, self.refresh_token = await auth.authenticate()

            with open(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json"), 'w') as f:
                json.dump({'token': self.token, 'refresh': self.refresh_token}, f)
        else:
            print("Cannot run authorization")

    async def reauth(self):
        print("Attempting to refresh access token")
        if bool(self.refresh_token):
            self.token, self.refresh_token = await refresh_access_token(self.refresh_token, self.config['DEFAULT']['TwitchAppId'], self.config['DEFAULT']['TwitchAppSecret'])
            await self.update_stored_creds(self.token, self.refresh_token)
        else:
            print("First auth not completed, trying now")
            await self.auth()

    # Run application
    async def run(self):
        # Use or generate auth
        if os.path.exists(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json")):
            # Get the broadcaster (for ID)
            with open(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json")) as f:
                creds = json.load(f)
                self.token = creds["token"]
                self.refresh_token = creds["refresh"]

                self.headers = {
                    'Authorization': f'Bearer {creds["token"]}',
                    'Client-Id': self.config['DEFAULT']['TwitchAppId'],
                    'Content-Type': 'application/json'
                }

                broad_request = requests.get(f"{ttsController.URI}/users?user_login={self.config['DEFAULT']['TargetChannel']}", headers=self.headers)
                self.broadcaster = broad_request.json()
                print(self.broadcaster)

        # Create the app for twitch message processing
        if not self.ws_app:
            print('Creating twitch websocket')
            websocket.setdefaulttimeout(10)
            self.ws_app = websocket.WebSocketApp(
                ttsController.WS_ENDPOINT,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )