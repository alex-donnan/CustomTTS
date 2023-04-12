from pydub import AudioSegment
from TTS.api import TTS
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.pubsub import PubSub
from twitchAPI.twitch import Twitch
from twitchAPI.types import AuthScope
from uuid import UUID
import configparser
import os
import queue
import requests
import urllib.parse

class ttsController:

    APP_ID = ''
    APP_SECRET = ''
    USER_SCOPE = [AuthScope.BITS_READ]
    PREFIXES = prefixes = ["Cheer", "hryCheer", "BibleThump", "cheerwhal", "Corgo", "uni", "ShowLove", "Party", "SeemsGood",
                           "Pride", "Kappa", "FrankerZ", "HeyGuys", "DansGame", "EleGiggle", "TriHard", "Kreygasm", "4Head",
                           "SwiftRage", "NotLikeThis", "FailFish", "VoHiYo", "PJSalt", "MrDestructoid", "bday", "RIPCheer",
                           "Shamrock"]

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.output_path = os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.wav")
        self.target_channel = self.config['DEFAULT']['TargetChannel']
        self.tts_queue = queue.Queue()
        self.tts_client = TTS(TTS.list_models()[0])

    def remove_cheermotes(raw_message):
        word_list = raw_message.split(" ")
        message = ""
        for word in word_list:
            if word.startswith(tuple(prefixes)) and word[-1].isdigit():
                continue
            message += word + " "
        message.strip()
        return message

    def worker(self):
        while True:
            if os.path.exists(self.output_path):
                continue
            # if Cheer in queue, process it
            item = self.tts_queue.get()
            message = remove_cheermotes(item['chat_message'])
            if item['bits_used'] == 2:
                # do Coqui voice (just default voice atm)
                self.tts_client.tts_to_file(text=message, file_path=self.output_path, speaker=self.tts_client.speakers[0],
                                       language=self.tts_client.languages[0])
                self.tts_queue.task_done()
            else:
                # Do brian
                url = 'https://api.streamelements.com/kappa/v2/speech?voice=Brian&text=' + urllib.parse.quote_plus(message)
                data = requests.get(url)
                with open(os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.mp3"), 'wb') as f:
                    f.write(data.content)
                f.close()
                sound = AudioSegment.from_mp3(os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.mp3"))
                sound.export(self.output_path, format="wav")
                os.remove(os.path.join(self.config['DEFAULT']['OutputDirectory'], "output.mp3"))

    async def on_cheer(self, uuid: UUID, data: dict) -> None:
        self.tts_queue.put(data)

    async def run(self):
        twitch = await Twitch(ttsController.APP_ID, ttsController.APP_SECRET)
        auth = UserAuthenticator(twitch, ttsController.USER_SCOPE, force_verify=False)
        token, refresh_token = await auth.authenticate()
        await twitch.set_user_authentication(token, ttsController.USER_SCOPE, refresh_token)
        user = await first(twitch.get_users(logins=[self.target_channel]))

        pubsub = PubSub(twitch)
        pubsub.start()
        uuid = await pubsub.listen_bits(user.id, ttsController.on_cheer)

        return (twitch, pubsub, uuid)

    async def kill(self, listener: tuple):
        twitch, pubsub, uuid = listener
        await pubsub.unlisten(uuid)
        pubsub.stop()
        await twitch.close()

    # Get Set

    def get_channel(self):
        return self.target_channel

    def set_channel(self, channel: str):
        self.target_channel = channel
        self.config.set('DEFAULT', 'TargetChannel', channel)

    def get_output(self):
        return self.output_path

    def set_output(self, output: str):
        self.output_path = os.path.join(output, 'output.wav')
        self.config.set('DEFAULT', 'OutputDirectory', output)

    def get_queue(self):
        return self.tts_queue