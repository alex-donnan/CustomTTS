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
import time
import urllib.parse
import websocket

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
    SUBS_ENDPOINT = '/eventsub/subscriptions' if not DEVMODE else 'http://localhost:8080/eventsub/subscriptions'
    SUBSCRIPTIONS = [
        'channel.subscription.message',
        'channel.subscription.gift',
        'channel.cheer'
    ]

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.output_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.wav")
        self.brian_output_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.mp3")
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

    # WebSocket event methods
    def on_open(self, ws):
        # update the color
        self.connected = True
        print('Connected to Twitch')

    def on_message(self, ws, msg):
        self.connected = True
        msg = json.loads(msg)
        if msg['metadata']['message_type'] == 'session_welcome':
            # session variables
            session_id = msg['payload']['session']['id']

            # TODO: get broadcaster ID from username with endpoint
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
                response = requests.post(ttsController.URI + ttsController.SUBS_ENDPOINT, json=sub_data, headers=self.headers)
                print(f'Subscription response: {response.text}')
        elif msg['metadata']['message_type'] == 'session_keepalive':
            keepalive = msg['metadata']['message_timestamp']
        elif msg['metadata']['message_type'] == 'notification':
            event = (msg['payload'])['event']
            if msg['payload']['subscription']['type'] == 'channel.subscription.gift':
                message = {
                    'user_name': event['user_name'],
                    'chat_message': 'Gift Sub Message',
                    'no_message': True
                }
                # add to tts_queue here
                print(message)
            elif msg['payload']['subscription']['type'] == 'channel.subscription.message':
                message = {
                    'user_name': event['user_name'],
                    'chat_message': event['message']['text']
                }
                # add to tts_queue here
                print(message)
            elif msg['payload']['subscription']['type'] == 'channel.cheer':
                message = {
                    'user_name': event['user_name'],
                    'chat_message': event['message']
                }
                # add to tts_queue here
                self.tts_queue.put(message['chat_message'])

    def on_error(self, ws, msg):
        print(f'An error has occurred: {msg}')

    def on_close(self, ws, close_status_code, msg):
        self.connected = False
        print('Closed')

    # Worker
    def worker(self):
        while True:
            # if Cheer in queue, process it
            if self.pause_flag:
                sleep(0.5)
                continue

            if self.clear_flag:
                if self.tts_queue.empty:
                    self.clear_flag = False
                    continue

            time.sleep(2)
            try:
                # hack to keep current TTS at top of visible list until it's played
                item = list(self.tts_queue.queue)[0]
            except IndexError:
                continue

            message = remove_cheermotes(item['chat_message'])

            message_list = self.split_message(message)
            self.do_speaking(message_list)

    def do_speaking(self, message_list):
        soundplay("assets/cheer.wav", block=True)
        sleep(0.25)
        for message_object in message_list:
            if self.clear_flag: continue
            voice = message_object['voice']
            message = message_object['message']
            if voice != 'brian' and voice in self.speaker_list.keys() \
                    and self.speaker_list[voice]['model'] in self.tts_synth.keys():
                message = convert_numbers(message)
                message = replace_emoji(message)
                # do Coqui voice (just default voice atm)
                self.tts_synth[self.speaker_list[voice]['model']] \
                    .save_wav(self.tts_synth[self.speaker_list[voice]['model']]
                              .tts(message, speaker_name=self.speaker_list[voice]['speaker'], language_name='en'),
                              self.output_path)

                self.currently_playing = soundplay(self.output_path)
                while getIsPlaying(self.currently_playing):
                    if self.clear_flag:
                        stopsound(self.currently_playing)
                    sleep(0.5)
                stopsound(self.currently_playing)
                os.remove(self.output_path)
            else:
                # Do brian
                url = 'https://api.streamelements.com/kappa/v2/speech?voice=Brian&text=' + urllib.parse.quote_plus(
                    message)
                data = requests.get(url)
                with open(self.brian_output_path, 'wb') as f:
                    f.write(data.content)
                f.close()
                self.currently_playing = soundplay(self.brian_output_path)
                while getIsPlaying(self.currently_playing):
                    if self.clear_flag:
                        stopsound(self.currently_playing)
                    sleep(0.5)
                stopsound(self.currently_playing)
                os.remove(self.brian_output_path)

            # hack to keep current TTS at top of visible list until it's played
        try:
            self.tts_queue.get(timeout=1)
        except queue.Empty:
            return
        self.tts_queue.task_done()

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

    def set_output(self, output: str):
        self.output_path = os.path.join(output, 'output.wav')
        self.config.set('DEFAULT', 'OutputDirectory', output)
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)