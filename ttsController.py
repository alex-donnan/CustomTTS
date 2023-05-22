import glob
from num2words import num2words
from preferredsoundplayer import *
from TTS.utils.synthesizer import Synthesizer
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.types import AuthScope
from uuid import UUID
import configparser
import emoji
import json
import os
import queue
import re
import requests
import string
import time
import threading
import urllib.parse
import websocket
import random

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
        if word.startswith(tuple(ttsController.PREFIXES)) and word[-1].isdigit():
            continue
        message += word + " "
    message.strip()
    return message


class ttsController:
    USER_SCOPE = [AuthScope.BITS_READ, AuthScope.CHANNEL_MODERATE, AuthScope.CHANNEL_READ_SUBSCRIPTIONS]
    PREFIXES = prefixes = ["Cheer", "hryCheer", "BibleThump", "cheerwhal", "Corgo", "uni", "ShowLove", "Party",
                           "SeemsGood",
                           "Pride", "Kappa", "FrankerZ", "HeyGuys", "DansGame", "EleGiggle", "TriHard", "Kreygasm",
                           "4Head",
                           "SwiftRage", "NotLikeThis", "FailFish", "VoHiYo", "PJSalt", "MrDestructoid", "bday",
                           "RIPCheer",
                           "Shamrock"]
    URI = 'https://api.twitch.tv/helix'
    WS_ENDPOINT = 'wss://eventsub.wss.twitch.tv/ws' if not DEVMODE else 'ws://127.0.0.1:8080/ws'
    SUBS_ENDPOINT = 'https://api.twitch.tv/helix/eventsub/subscriptions' if not DEVMODE else 'http://localhost:8080/eventsub/subscriptions'
    SUBSCRIPTIONS = [
        'channel.subscription.message',
        'channel.subscription.gift',
        'channel.cheer'
    ]

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.output_path = self.config['DEFAULT']['OutputDirectory']
        self.credentials_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "credentials.json")
        
        self.target_channel = self.config['DEFAULT']['TargetChannel']
        self.app_id = self.config['DEFAULT']['TwitchAppId']
        self.app_secret = self.config['DEFAULT']['TwitchAppSecret']
        self.headers = {}
        self.broadcaster = ''
        self.wsapp = None

        self.model_dir = self.config.get('DEFAULT', 'ModelDir', fallback='./models/')
        root, dirs, files = os.walk(self.model_dir).__next__()

        self.tts_synth = {}

        for model_name in dirs:
            model_path = os.path.join(self.model_dir, model_name,
                                      glob.glob('*.pth', root_dir=os.path.join(self.model_dir, model_name))[0])
            config_path = os.path.join(self.model_dir, model_name, 'config.json')
            speakers_path = os.path.join(self.model_dir, model_name, 'speakers.pth')
            languages_path = os.path.join(self.model_dir, model_name, 'language_ids.json')
            if not (os.path.exists(model_path) and os.path.exists(config_path)):
                print('Missing file for model in directory: ' + model_name)
                continue
            new_synth = Synthesizer(tts_checkpoint=model_path,
                                    tts_config_path=config_path,
                                    tts_speakers_file=speakers_path if os.path.exists(speakers_path) else None,
                                    tts_languages_file=languages_path if os.path.exists(languages_path) else None)
            self.tts_synth[model_name] = new_synth

        self.tts_queue = queue.Queue()

        self.currently_playing = None
        self.pause_flag = False
        self.clear_flag = False
        self.speaker_list = eval(self.config['DEFAULT']['Speakers'])
        self.connected = False

    def generate_fname(self):
        fname = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # In the highly unlikely event it exists already, recurse
        if os.path.exists(os.path.join(self.output_path, fname + '.wav')):
            fname = self.generate_fname()
        return fname

    def generate_wav(self, msg):
        for message_object in msg['message']:
            output_file = os.path.join(self.output_path, self.generate_fname())

            if self.clear_flag: continue
            voice = message_object['voice']
            message = message_object['message']
            print(f'New file for {voice}: {output_file}')

            # Select voice generator
            if message.strip() != '':
                if voice != 'brian' and voice in self.speaker_list.keys() \
                        and self.speaker_list[voice]['model'] in self.tts_synth.keys():
                    message = convert_numbers(message)
                    message = replace_emoji(message)

                    # generate
                    self.tts_synth[self.speaker_list[voice]['model']] \
                        .save_wav(self.tts_synth[self.speaker_list[voice]['model']]
                                  .tts(message, speaker_name=self.speaker_list[voice]['speaker'], language_name='en'),
                                  output_file + '.wav')
                else:
                    # Do brian
                    url = 'https://api.streamelements.com/kappa/v2/speech?voice=Brian&text=' + urllib.parse.quote_plus(
                        message)
                    data = requests.get(url)
                    with open(output_file + '.mp3', 'wb') as f:
                        f.write(data.content)
                    f.close()

                # Put the file in the play queue
                message_object['filename'] = output_file

        print(msg)
        self.tts_queue.put(msg)

    def play_wav(self, message_list):
        soundplay("assets/cheer.wav", block=True)
        sleep(0.25)

        for message_object in message_list:
            file = message_object['filename'] + ('.wav' if message_object['voice'] != 'brian' else '.mp3')
            self.currently_playing = soundplay(file)
            while getIsPlaying(self.currently_playing):
                if self.clear_flag:
                    stopsound(self.currently_playing)
                sleep(0.5)
            stopsound(self.currently_playing)

            os.remove(file)

        # Hack way to let GUI know to decrease the visible messages
        self.currently_playing = None
        try:
            self.tts_queue.get(timeout=1)
        except queue.Empty:
            return
        self.tts_queue.task_done()

    # WebSocket event methods
    def on_open(self, ws):
        # update the color
        self.connected = True
        print('Connected to Twitch')

    def on_message(self, ws, msg):
        def run(self, message):
            message['message'] = remove_cheermotes(message['chat_message'])
            message['message'] = self.split_message(message['message'])
            self.generate_wav(message)
        
        msg = json.loads(msg)
        if msg['metadata']['message_type'] == 'session_welcome':
            # session variables
            session_id = msg['payload']['session']['id']

            for sub_type in ttsController.SUBSCRIPTIONS:
                sub_data = {
                    'type': sub_type,
                    'version': '1',
                    'condition': {
                        'broadcaster_user_id': self.broadcaster['data'][0]['id']
                   },
                    'transport': {
                        'method': 'websocket',
                        'session_id': session_id
                    }
                }
                response = requests.post(ttsController.SUBS_ENDPOINT, json=sub_data, headers=self.headers)
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

            threading.Thread(target=run, args=[self, message], daemon=True).start()

    def on_error(self, ws, msg):
        print(f'An error has occurred: {msg}')

    def on_close(self, ws, close_status_code, msg):
        self.connected = False
        print('Closed')

    # Worker
    def worker(self):
        while True:
            if self.clear_flag:
                if self.tts_queue.empty:
                    self.clear_flag = False
                    continue

            if self.pause_flag:
                sleep(0.5)
                continue

            time.sleep(2)
            try:
                item = list(self.tts_queue.queue)[0]
            except IndexError:
                continue

            if "no_message" in item and item["no_message"]:
                soundplay("assets/cheer.wav", block=True)
                try:
                    self.tts_queue.get(timeout=1)
                except queue.Empty:
                    continue
                self.tts_queue.task_done()
                continue

            print(item)
            self.play_wav(item['message'])

    # Utilites
    def split_message(self, message):
        sub_messages = message.split('#')
        while '' in sub_messages:
            sub_messages.remove('')
        message_list = []
        for sub_message in sub_messages:
            if sub_message.split()[0].lower() in self.speaker_list.keys() or sub_message.split()[0].lower() == "brian":
                voice = sub_message.split()[0].lower()
                sub_message_object = {
                    'voice': voice,
                    'message': sub_message.removeprefix(sub_message.split()[0]).strip()
                }
                message_list.append(sub_message_object)
            else:
                if len(message_list) != 0:
                    message_list[sub_messages.index(sub_message) - 1]['message'] += ' #' + sub_message
                else:
                    sub_message_object = {
                        'voice': 'brian',
                        'message': sub_message
                    }
                    message_list.append(sub_message_object)
        return message_list

    async def update_stored_creds(self, token, refresh):
        with open(self.credentials_path, 'w') as f:
            json.dump({'token': token, 'refresh': refresh}, f)
    
    async def run(self):
        # Just use pre-built twitch auth
        twitch = await Twitch(self.app_id, self.app_secret)
        twitch.user_auth_refresh_callback = self.update_stored_creds
        needs_auth = True

        # Use or generate auth
        if os.path.exists(self.credentials_path):
            with open(self.credentials_path) as f:
                creds = json.load(f)
            try:
                await twitch.set_user_authentication(creds['token'], ttsController.USER_SCOPE, creds['refresh'])
                user = await first(twitch.get_users(logins=[self.target_channel]))
            except Exception as ex:
                print(f'Stored token invalid : {ex}')
            else:
                needs_auth = False

        if needs_auth:
            auth = UserAuthenticator(twitch, ttsController.USER_SCOPE)
            token, refresh_token = await auth.authenticate()
            with open(self.credentials_path, 'w') as f:
                json.dump({'token': token, 'refresh': refresh_token}, f)
            await twitch.set_user_authentication(token, ttsController.USER_SCOPE, refresh_token)
            user = await first(twitch.get_users(logins=[self.target_channel]))

        # Get the broadcaster (for ID)
        with open(self.credentials_path) as f:
            creds = json.load(f)

            self.headers = {
                'Authorization': f'Bearer {creds["token"]}',
                'Client-Id': self.app_id,
                'Content-Type': 'application/json'
            }

            broad_request = requests.get(f'{ttsController.URI}/users?user_login={self.target_channel}', headers=self.headers)
            self.broadcaster = broad_request.json()

        # Create the socket for threading
        print('Creating websocket')
        websocket.setdefaulttimeout(10)
        self.wsapp = websocket.WebSocketApp(ttsController.WS_ENDPOINT,
            on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)

    # Setters
    def set_channel(self, channel: str):
        self.target_channel = channel
        self.config.set('DEFAULT', 'TargetChannel', channel)
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)