from num2words import num2words
from preferredsoundplayer import *
from TTS.utils.synthesizer import Synthesizer
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

import asyncio
import configparser
import emoji
import glob
import json
import os
import math
import queue
import random
import re
import requests
import shutil
import string
import threading
import urllib.parse
import websocket
import winsdk.windows.media.control as wmc

DEVMODE = False

def replace_emoji(message):
    message = re.sub(':[\\w_]+:', lambda m: re.sub('[:_]', ' ', m.group()), emoji.demojize(message))
    return message


def convert_numbers(message):
    message = re.sub('£(\\d+)', lambda m: num2words(m.group(1), to='currency', currency='GBP'), message)
    message = re.sub('\\$(\\d+)', lambda m: num2words(m.group(1), to='currency', currency='USD'), message)
    message = re.sub('(\\d+)', lambda m: num2words(m.group()), message)
    return message


def remove_cheermotes(raw_message):
    word_list = raw_message.split(" ")
    message = ""
    for word in word_list:
        if word.lower().startswith(tuple(ttsController.PREFIXES)) and word[-1].isdigit():
            continue
        message += word + " "
    message.strip()
    return message


async def get_media_session():
    sessions = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = sessions.get_current_session()
    return session


class ttsController:
    USER_SCOPE = [AuthScope.BITS_READ, AuthScope.CHANNEL_MODERATE, AuthScope.CHANNEL_READ_SUBSCRIPTIONS]
    PREFIXES = prefixes = ["cheer", "hrycheer", "biblethump", "cheerwhal", "corgo", "uni", "showlove", "party",
                           "seemsgood",
                           "pride", "kappa", "frankerz", "heyguys", "dansgame", "elegiggle", "trihard", "kreygasm",
                           "4head",
                           "swiftrage", "notlikethis", "failfish", "vohiyo", "pjsalt", "mrdestructoid", "bday",
                           "ripcheer",
                           "shamrock"]
    URI = 'https://api.twitch.tv/helix'
    WS_ENDPOINT = 'wss://eventsub.wss.twitch.tv/ws' if not DEVMODE else 'ws://127.0.0.1:8080/ws'
    SUBS_ENDPOINT = 'https://api.twitch.tv/helix/eventsub/subscriptions' if not DEVMODE else 'http://127.0.0.1:8080/eventsub/subscriptions'
    SUBSCRIPTIONS = [
        'channel.subscription.message',
        'channel.subscription.gift',
        'channel.cheer'
    ]
    NOTES = ['a','ab','b','bb','c','cb','d','db','e','eb','f','fb','g','gb','r']
    BEAT = [0, 4, 2, -2, 1]

    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.output_path = self.config['DEFAULT']['OutputDir']
        self.asset_path = self.config['DEFAULT']['AssetsDir']
        self.credentials_path = os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json")
        
        self.target_channel = self.config['DEFAULT']['TargetChannel']
        self.app_id = self.config['DEFAULT']['TwitchAppId']
        self.app_secret = self.config['DEFAULT']['TwitchAppSecret']
        self.headers = {}
        self.subscriptions = []
        self.broadcaster = ''
        self.wsapp = None

        self.model_dir = self.config.get('DEFAULT', 'ModelDir', fallback='./models/')
        root, dirs, files = os.walk(self.model_dir).__next__()

        self.tts_synth = {}

        for model_name in dirs:
            self.add_model(model_name)

        self.gen_queue = queue.Queue()
        self.tts_queue = queue.Queue()
        self.tts_text = []

        self.gen_worker_thread = None
        self.tts_worker_thread = None
        self.gen_thread = None
        self.tts_thread = None 

        self.currently_playing = None
        self.skip_flag = False
        self.pause_flag = False
        self.clear_flag = False
        self.speaker_list = eval(self.config['DEFAULT']['Speakers'])
        self.sound_list = eval(self.config['DEFAULT']['Sounds'])
        self.connected = False

    # Worker
    def gen_worker(self):
        while True:
            try:
                self.gen_thread = self.gen_queue.get(timeout=1)
                self.gen_thread()
            except (queue.Empty, IndexError):
                continue

    def tts_worker(self):
        while True:
            if self.clear_flag:
                if self.tts_queue.empty() and self.gen_queue.empty():
                    self.clear_flag = False
                    continue

            # Play any sounds
            if not self.pause_flag:
                try:
                    self.tts_thread = self.tts_queue.get(timeout=1)
                    self.tts_thread()
                except (queue.Empty, IndexError):
                    self.skip_flag = False
                    continue
            else:
                sleep(1)

    # Audio generation or playback
    def generate_fname(self):
        fname = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # In the highly unlikely event it exists already, recurse
        if os.path.exists(os.path.join(self.output_path, fname + '.wav')):
            fname = self.generate_fname()
        return fname

    def generate_wav(self, msg):
        user = msg['user_name']
        for id_msg, message_object in enumerate(msg['message']):
            output_file = self.generate_fname()
            prepend_file = None

            if self.clear_flag: continue
            print(message_object)
            voice = message_object['voice']
            message = message_object['message']

            # Select voice generator
            if voice != 'brian' and voice in self.speaker_list.keys() \
                    and self.speaker_list[voice]['model'] in self.tts_synth.keys():
                message = convert_numbers(message)
                message = replace_emoji(message)

                # Generate
                self.tts_synth[self.speaker_list[voice]['model']] \
                    .save_wav(self.tts_synth[self.speaker_list[voice]['model']]
                              .tts(message, speaker_name=self.speaker_list[voice]['speaker'], language_name='en'),
                              self.output_path + output_file + '.wav')
            elif voice in self.sound_list.keys():
                # Dear god forgive me for this sin
                shutil.copy(os.path.join(self.asset_path, self.sound_list[voice]), self.output_path + output_file + os.path.splitext(self.sound_list[voice])[-1])
            elif voice == 'lute':
                # MUSIC
                try:
                    url = f'https://luteboi.com/lute/?message={urllib.parse.quote_plus("#lute " + message)}&key={urllib.parse.quote_plus(user)}'
                    data = requests.get(url)
                    with open(self.output_path + output_file + '.wav', 'wb') as f:
                        f.write(data.content)
                except Exception as ex:
                    print(f'Generation done broke. Sorry luter: {ex}')
                    shutil.copyfile('./assets/broken.wav', self.output_path + output_file + '.wav')
            else:
                # Do Brian
                url = 'https://api.streamelements.com/kappa/v2/speech?voice=Brian&text=' + urllib.parse.quote_plus(
                    message)
                data = requests.get(url)
                with open(self.output_path + output_file + '.mp3', 'wb') as f:
                    f.write(data.content)

            # Put the file in the play queue
            print(f'New file for {voice}: {message}: {output_file}')
            message_object['filename'] = output_file

        self.tts_queue.put(lambda: self.play_wav(msg['message']))
        self.gen_thread = None
        self.gen_queue.task_done()
        return

    def play_wav(self, message_list):
        soundplay("assets/cheer.wav", block=True)
        sleep(0.25)
        media_paused = False
        session = None
        for message_object in message_list:
            if message_object['voice'] == "lute":
                session = asyncio.run(get_media_session())
                if session is not None:
                    media_paused = session.get_playback_info().playback_status.value == 4
                    session.try_pause_async()

            file = None
            for f in os.listdir(self.output_path):
                if message_object['filename'] == f[0:6]: file = self.output_path + f
            try:
                if file:
                    self.currently_playing = soundplay(file)
                    while getIsPlaying(self.currently_playing):
                        if self.clear_flag or self.skip_flag:
                            stopsound(self.currently_playing)
                            self.skip_flag = False
                        sleep(0.1)
                    stopsound(self.currently_playing)
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
            # session variables
            session_id = msg['payload']['session']['id']

            init_check = requests.get(ttsController.SUBS_ENDPOINT + '?status=enabled', headers=self.headers).json()
            sub_check = [sub['type'] for sub in init_check['data']]
            print(f'Previous subscriptions that are active: {sub_check}\nThese will be skipped')

            for sub in self.subscriptions:
                if sub not in sub_check:
                    self.subscriptions.remove(sub)

            for sub_type in ttsController.SUBSCRIPTIONS:
                if sub_type not in self.subscriptions:
                    sub_data = {
                        'type': sub_type,
                        'version': '1',
                        'condition': {
                            'broadcaster_user_id': self.broadcaster['data'][0]['id'],
                            'user_id': self.broadcaster['data'][0]['id']
                       },
                        'transport': {
                            'method': 'websocket',
                            'session_id': session_id
                        }
                    }

                    response = requests.post(ttsController.SUBS_ENDPOINT, json=sub_data, headers=self.headers)
                    self.subscriptions.append(sub_type);
                    print(f'Subscription response: {response.json()}')
        elif msg['metadata']['message_type'] == 'notification':
            event = (msg['payload'])['event']
            message = {}
            if msg['payload']['subscription']['type'] == 'channel.subscription.gift':
                message = {
                    'user_name': event['user_name'],
                    'chat_message': f"{event['total']} Gifted Sub{'' if event['total'] == 1 else 's'}",
                    'no_message': True
                }
            elif msg['payload']['subscription']['type'] == 'channel.subscription.message':
                message = {
                    'user_name': event['user_name'],
                    'chat_message': event['message']['text']
                }
            elif msg['payload']['subscription']['type'] == 'channel.cheer':
                message = {
                    'user_name': event['user_name'],
                    'chat_message': event['message']
                }

            message['message'] = remove_cheermotes(message['chat_message'])
            message['message'] = self.split_message(message['message'])

            # Append to out text
            self.tts_text.append(message)
            self.gen_queue.put(lambda: self.generate_wav(message))

    def on_error(self, ws, msg):
        print(f'An error has occurred: {msg}')
        return

    def on_close(self, ws, close_status_code, msg):
        self.connected = False
        print('Closed')
        return

    # Utilites
    def split_message(self, message):
        sub_messages = message.split('#')
        while '' in sub_messages:
            sub_messages.remove('')

        message_list = []
        voice = 'brian'
        for i, sub_message in enumerate(sub_messages):
            # Should we consider the first word in message a keyword
            key_check = (i > 0 or (i == 0 and message[0] == '#'))

            # Check for sounds to remove, then re-check speakers
            if key_check and sub_message.split()[0].lower() in self.sound_list.keys():
                sound = sub_message.split()[0]
                sub_message = sub_message.replace(sound, voice, 1)
                sub_message_object = {
                    'voice': sound.lower(),
                    'message': '-'
                }
                message_list.append(sub_message_object)

            # Check your speakers
            if key_check and (sub_message.split()[0].lower() in self.speaker_list.keys() or sub_message.split()[0].lower() in ('brian', 'lute')):
                voice = sub_message.split()[0].lower()
                sub_message_object = {
                    'voice': voice,
                    'message': sub_message.removeprefix(sub_message.split()[0]).strip()
                }
                if sub_message.removeprefix(sub_message.split()[0]).strip() != '': message_list.append(sub_message_object)
            else:
                if len(message_list) != 0:
                    message_list[-1]['message'] += ' #' + sub_message
                else:
                    sub_message_object = {
                        'voice': 'brian',
                        'message': sub_message
                    }

                    if sub_message.strip() != '': message_list.append(sub_message_object)

        return message_list

    async def update_stored_creds(self, token, refresh):
        print("Access token refreshed successfully")
        with open(self.credentials_path, 'w') as f:
            json.dump({'token': token, 'refresh': refresh}, f)

    async def auth(self):
        # Just use pre-built twitch auth
        twitch = await Twitch(self.app_id, self.app_secret)

        auth = UserAuthenticator(twitch, ttsController.USER_SCOPE)
        self.token, self.refresh_token = await auth.authenticate()

        with open(self.credentials_path, 'w') as f:
            json.dump({'token': self.token, 'refresh': self.refresh_token}, f)

    async def reauth(self):
        print("Attempting to refresh access token")
        self.token, self.refresh_token = await refresh_access_token(self.refresh_token, self.app_id, self.app_secret)
        await self.update_stored_creds(self.token, self.refresh_token)

    async def run(self):
        # Use or generate auth
        if os.path.exists(self.credentials_path):
            # Get the broadcaster (for ID)
            with open(self.credentials_path) as f:
                creds = json.load(f)
                self.token = creds["token"]
                self.refresh_token = creds["refresh"]

                self.headers = {
                    'Authorization': f'Bearer {creds["token"]}',
                    'Client-Id': self.app_id,
                    'Content-Type': 'application/json'
                }

                broad_request = requests.get(f'{ttsController.URI}/users?user_login={self.target_channel}',
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

    # Setters
    def set_channel(self, channel: str):
        self.target_channel = channel
        self.config.set('DEFAULT', 'TargetChannel', channel)
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)

    def add_model(self, model_name):
        model_path = os.path.join(self.model_dir, model_name,
                                      glob.glob('*.pth', root_dir=os.path.join(self.model_dir, model_name))[0])
        config_path = os.path.join(self.model_dir, model_name, 'config.json')
        speakers_path = os.path.join(self.model_dir, model_name, 'speakers.pth')
        languages_path = os.path.join(self.model_dir, model_name, 'language_ids.json')
        if not (os.path.exists(model_path) and os.path.exists(config_path)):
            print('Missing file for model in directory: ' + model_name)
            return
        new_synth = Synthesizer(tts_checkpoint=model_path,
                                tts_config_path=config_path,
                                tts_speakers_file=speakers_path if os.path.exists(speakers_path) else None,
                                tts_languages_file=languages_path if os.path.exists(languages_path) else None)
        self.tts_synth[model_name] = new_synth
        return