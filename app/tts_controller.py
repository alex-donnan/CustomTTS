from actions import *
from preferredsoundplayer import *
from TTS.utils.synthesizer import Synthesizer
from tts_utils import *
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

import asyncio
import configparser
import glob
import json
import os
import queue
import re
import requests
import shutil
import threading
import websocket
import websockets
import winsdk.windows.media.control as wmc

DEVMODE = False

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
        self.token = None
        self.refresh_token = None
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.headers = {}
        self.subscriptions = []
        self.broadcaster = {}
        self.wsapp = None

        root, dirs, files = os.walk(self.config['DEFAULT']['ModelDir']).__next__()
        self.tts_synth = {}
        for model_name in dirs:
            self.add_model(model_name)

        self.gen_queue = queue.Queue()
        self.gen_worker_thread = None
        self.gen_thread = None
        self.tts_queue = queue.Queue()
        self.tts_worker_thread = None
        self.tts_thread = None

        self.tts_text = []

        self.currently_playing = None
        self.speaker_list = eval(self.config['AI']['speakers'])
        self.sound_list = eval(self.config['SOUND']['sounds'])
        self.connected = False

        # actions
        self.actions = {
            'SESSION': sessionStartAction(self, self.config),
            'AI': aiAction(self, self.config, 'AI'),
            'CHAT': chatAction(self, self.config),
            'LUTE': luteAction(self, self.config, 'LUTE'),
            'SOUND': soundAction(self, self.config, 'SOUND'),
            'TTS': ttsAction(self, self.config, 'TTS'),
        }

        # for websocket server
        self.current_speaker = "none"
        self.websocket_server_thread = threading.Thread(target=self.start_websocket_server, daemon=True)
        self.websocket_server_thread.start()
        self.websocket_server = None

    # Workers
    def gen_worker(self):
        while True:
            try:
                self.gen_thread = self.gen_queue.get(timeout=1)
                self.gen_thread()
            except (queue.Empty, IndexError):
                continue

    def tts_worker(self):
        while True:
            if self.config['FLAGS'].getboolean('clear'):
                if self.tts_queue.empty() and self.gen_queue.empty():
                    self.config.set('FLAGS', 'clear', 'False')
                    self.save_config()
                    continue

            # Play any sounds
            if not self.config['FLAGS'].getboolean('pause'):
                try:
                    self.tts_thread = self.tts_queue.get(timeout=1)
                    self.tts_thread()
                except (queue.Empty, IndexError):
                    self.config.set('FLAGS', 'skip', 'False')
                    self.save_config()
                    continue
            else:
                self.current_speaker = "paused"
                sleep(1)

    # Websocket service
    async def websocket_server_worker(self, websocket_server):
        self.websocket_server = websocket_server
        while True:
            try:
                client_message = await websocket_server.recv()
            except websockets.ConnectionClosed:
                print(f"Websocket server connection terminated")
                break

            response = None
            if client_message == "Connect":
                response = "Connected"
                print("Client connected, sending connection response.")
            if client_message.split(':')[0] == "Speaker" and client_message.split(':')[1] != self.current_speaker:
                response = f"Speaker:{self.current_speaker}"
                print(f"Client speaker update: {response}")
            
            if response:
                try:
                    await websocket_server.send(response)
                except websockets.ConnectionClosed:
                    print("Websocket server connection terminated")
                    break

    def start_websocket_server(self):
        print("Starting websocket server")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create and start the server within the running loop
        async def run_server():
            async with websockets.serve(self.websocket_server_worker, 'localhost', 1515):
                await asyncio.Future()  # Run forever

        loop.run_until_complete(run_server())

    def generate(self, message_list):
        audio_list = []
        failed = False
        for msg in message_list:
            try:
                msg_obj = self.actions[msg['type']].generate(msg)
                if bool(msg_obj):
                    audio_list.append(msg_obj)
            except Exception as e:
                print('Failed to generate audio, aborting message')
                print(e)
                failed = True
                break

        if not failed:
            self.tts_queue.put(lambda: self.play_wav(audio_list))
        self.gen_thread = None
        self.gen_queue.task_done()
        return

    def play_wav(self, audio_list):
        self.current_speaker = "none"
        soundplay("assets/cheer.wav", block=True)
        sleep(0.25)
        media_paused = False
        session = None
        for msg_obj in audio_list:
            if msg_obj['type'] == "lute" and self.config['LUTE'].getboolean('pause_music'):
                session = asyncio.run(get_media_session())
                if session is not None:
                    media_paused = session.get_playback_info().playback_status.value == 4
                    session.try_pause_async()

            file = None
            for f in os.listdir(self.config['DEFAULT']['outputdir']):
                if msg_obj['filename'] == f: file = self.config['DEFAULT']['outputdir'] + f
            try:
                if file:
                    sound_muted = self.config[msg_obj['type']].getboolean('active')

                    if msg_obj['type'] not in self.sound_list.keys() and not sound_muted:
                        self.current_speaker = msg_obj['type']
                        sleep(0.5)

                    if not sound_muted:
                        self.currently_playing = soundplay(file)
                        while getIsPlaying(self.currently_playing):
                            if self.config['FLAGS'].getboolean('clear') or self.config['FLAGS'].getboolean('skip'):
                                stopsound(self.currently_playing)
                                self.config.set('FLAGS', 'skip', str(False))
                            sleep(0.1)

                        stopsound(self.currently_playing)

                    self.current_speaker = 'none' if not self.config['FLAGS'].getboolean('pause') else 'paused'
                    os.remove(file)
            except:
                print(f'Could not play file.')

            if session is not None and media_paused:
                session.try_play_async()
                media_paused = False

        # Hack way to let GUI know to decrease the visible messages?
        self.currently_playing = None
        self.tts_thread = None
        self.tts_queue.task_done()

        # Remove from out text
        self.tts_text = self.tts_text[1:]
        return

    # WebSocket event methods
    def on_open(self, ws):
        # update the color
        self.connected = True
        try:
            print('Starting worker thread.')

            if not self.tts_worker_thread:
                self.tts_worker_thread = threading.Thread(target=self.tts_worker, daemon=True)
            if self.tts_worker_thread and not self.tts_worker_thread.is_alive():
                self.tts_worker_thread.start()

            if not self.gen_worker_thread:
                self.gen_worker_thread = threading.Thread(target=self.gen_worker, daemon=True)
            if self.gen_worker_thread and not self.gen_worker_thread.is_alive():
                self.gen_worker_thread.start()
        except:
            return
        print('Connected to Twitch')

    def on_message(self, ws, msg):
        msg = json.loads(msg)

        if msg['metadata']['message_type'] == 'session_welcome':
            self.actions['SESSION'].action(msg)

        if msg['metadata']['message_type'] != 'notification': return

        message_list = []
        message = msg['payload']['event']['message']
        if type(message) == dict:
            message = message['text']

        for sub_message in re.split(r'[#!]', message):
            for action in self.actions.values():
                if action.validate(msg, sub_message):
                    msg_obj = action.action(msg)
                    if bool(msg_obj):
                        message_list.append(msg_obj)

        if len(message_list) > 0:
            self.tts_text.append(message)

        self.gen_queue.put(lambda: self.generate(message_list))

                
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
        twitch = await Twitch(self.config['DEFAULT']['TwitchAppId'], self.config['DEFAULT']['TwitchAppSecret'])

        auth = UserAuthenticator(twitch, ttsController.USER_SCOPE)
        self.token, self.refresh_token = await auth.authenticate()

        with open(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json"), 'w') as f:
            json.dump({'token': self.token, 'refresh': self.refresh_token}, f)

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

                broad_request = requests.get(f"{ttsController.URI}/users?user_login={self.config['DEFAULT']['TargetChannel']}",
                                             headers=self.headers)
                self.broadcaster = broad_request.json()

                print(self.broadcaster)

        # Create the socket for threading
        if not self.wsapp:
            print('Creating websocket')
            websocket.setdefaulttimeout(10)
            self.wsapp = websocket.WebSocketApp(ttsController.WS_ENDPOINT,
                                                on_open=self.on_open, on_message=self.on_message,
                                                on_error=self.on_error, on_close=self.on_close)

    # Config
    def save_config(self):
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)

    # Add new model (?)
    def add_model(self, model_name):
        model_path = os.path.join(self.config['DEFAULT']['ModelDir'], model_name,
                                  glob.glob('*.pth', root_dir=os.path.join(self.config['DEFAULT']['ModelDir'], model_name))[0])
        config_path = os.path.join(self.config['DEFAULT']['ModelDir'], model_name, 'config.json')
        speakers_path = os.path.join(self.config['DEFAULT']['ModelDir'], model_name, 'speakers.pth')
        languages_path = os.path.join(self.config['DEFAULT']['ModelDir'], model_name, 'language_ids.json')
        if not (os.path.exists(model_path) and os.path.exists(config_path)):
            print('Missing file for model in directory: ' + model_name)
            return
        new_synth = Synthesizer(tts_checkpoint=model_path,
                                tts_config_path=config_path,
                                tts_speakers_file=speakers_path if os.path.exists(speakers_path) else None,
                                tts_languages_file=languages_path if os.path.exists(languages_path) else None)
        self.tts_synth[model_name] = new_synth
        return
