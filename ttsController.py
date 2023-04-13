from num2words import num2words
from playsound import playsound
from TTS.api import TTS
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
    VOICES = voices = ["#harry", "#iskall", "#lewis"]

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.output_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.wav")
        self.brian_output_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.mp3")
        self.credentials_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "credentials.json")
        self.target_channel = self.config['DEFAULT']['TargetChannel']
        self.app_id = self.config['DEFAULT']['TwitchAppId']
        self.app_secret = self.config['DEFAULT']['TwitchAppSecret']
        self.tts_queue = queue.Queue()
        self.tts_client = TTS(TTS.list_models()[0])
        self.pause_flag = False

    def worker(self):
        while True:
            time.sleep(2)

            # if Cheer in queue, process it
            if self.pause_flag:
                continue

            try:
                item = self.tts_queue.get(timeout=1)
            except queue.Empty:
                continue

            message = remove_cheermotes(item['chat_message'])
            if item['bits_used'] == 2:
                message = convert_numbers(message)
                message = replace_emoji(message)
                # do Coqui voice (just default voice atm)
                self.tts_client.tts_to_file(text=message, file_path=self.output_path,
                                            speaker=self.tts_client.speakers[0],
                                            language=self.tts_client.languages[0])
                playsound(self.output_path)
                os.remove(self.output_path)
                self.tts_queue.task_done()
            else:
                # Do brian
                url = 'https://api.streamelements.com/kappa/v2/speech?voice=Brian&text=' + urllib.parse.quote_plus(
                    message)
                data = requests.get(url)
                with open(self.brian_output_path, 'wb') as f:
                    f.write(data.content)
                f.close()
                playsound(self.brian_output_path)
                os.remove(self.brian_output_path)
                self.tts_queue.task_done()

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


    def set_output(self, output: str):
        self.output_path = os.path.join(output, 'output.wav')
        self.config.set('DEFAULT', 'OutputDirectory', output)


    def set_queue(self, queue: queue):
        self.tts_queue = queue