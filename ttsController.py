import glob
from num2words import num2words
from preferredsoundplayer import *
from TTS.utils.synthesizer import Synthesizer
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.pubsub import PubSub
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
    USER_SCOPE = [AuthScope.BITS_READ, AuthScope.CHANNEL_MODERATE]
    PREFIXES = prefixes = ["Cheer", "hryCheer", "BibleThump", "cheerwhal", "Corgo", "uni", "ShowLove", "Party",
                           "SeemsGood",
                           "Pride", "Kappa", "FrankerZ", "HeyGuys", "DansGame", "EleGiggle", "TriHard", "Kreygasm",
                           "4Head",
                           "SwiftRage", "NotLikeThis", "FailFish", "VoHiYo", "PJSalt", "MrDestructoid", "bday",
                           "RIPCheer",
                           "Shamrock"]

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.output_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.wav")
        self.brian_output_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.mp3")
        self.credentials_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "credentials.json")
        self.target_channel = self.config['DEFAULT']['TargetChannel']
        self.app_id = self.config['DEFAULT']['TwitchAppId']
        self.app_secret = self.config['DEFAULT']['TwitchAppSecret']

        self.model_dir = self.config.get('DEFAULT', 'ModelDir', fallback='./models/')
        root, dirs, files = os.walk(self.model_dir).__next__()

        self.tts_synth = {}

        for model_name in dirs:
            model_path = os.path.join(self.model_dir, model_name,
                                      glob.glob('*.pth', root_dir=os.path.join(self.model_dir, model_name))[0])
            config_path = os.path.join(self.model_dir, model_name, 'config.json')
            speakers_path = os.path.join(self.model_dir, model_name, 'speakers.json')
            languages_path = os.path.join(self.model_dir, model_name, 'language_ids.json')
            if not (os.path.exists(model_path) and os.path.exists(config_path)):
                print('Missing file for model in directory: ' + model_name)
                continue
            new_synth = Synthesizer(model_path, config_path,
                                    speakers_path if os.path.exists(speakers_path) else None,
                                    languages_path if os.path.exists(languages_path) else None)
            self.tts_synth[model_name] = new_synth

        self.tts_queue = queue.Queue()

        self.currently_playing = None
        self.pause_flag = False
        self.clear_flag = False
        self.speaker_list = eval(self.config['DEFAULT']['Speakers'])

    def worker(self):
        while True:
            # if Cheer in queue, process it
            if self.pause_flag:
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
        for message_object in message_list:
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
        self.tts_queue.get()
        self.tts_queue.task_done()

    def split_message(self, message):
        sub_messages = message.split('#')
        while '' in sub_messages:
            sub_messages.remove('')
        message_list = []
        for sub_message in sub_messages:
            if sub_message.split()[0].lower() in self.speaker_list.keys():
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

    async def on_cheer(self, uuid: UUID, data: dict) -> None:
        self.tts_queue.put(data)

    async def run(self):
        twitch = await Twitch(self.app_id, self.app_secret)
        twitch.user_auth_refresh_callback = self.update_stored_creds
        needs_auth = True
        if os.path.exists(self.credentials_path):
            with open(self.credentials_path) as f:
                creds = json.load(f)
            try:
                await twitch.set_user_authentication(creds['token'], ttsController.USER_SCOPE, creds['refresh'])
                user = await first(twitch.get_users(logins=[self.target_channel]))
            except:
                print('stored token invalid, refreshing...')
            else:
                needs_auth = False

        if needs_auth:
            auth = UserAuthenticator(twitch, ttsController.USER_SCOPE)
            token, refresh_token = await auth.authenticate()
            with open(self.credentials_path, 'w') as f:
                json.dump({'token': token, 'refresh': refresh_token}, f)
            await twitch.set_user_authentication(token, ttsController.USER_SCOPE, refresh_token)
            user = await first(twitch.get_users(logins=[self.target_channel]))

        pubsub = PubSub(twitch)
        pubsub.start()
        uuid = await pubsub.listen_bits(user.id, ttsController.on_cheer)

        return twitch, pubsub, uuid

    async def kill(self, listener: tuple):
        twitch, pubsub, uuid = listener
        await pubsub.unlisten(uuid)
        pubsub.stop()
        await twitch.close()

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
