from django.apps import AppConfig
from django.conf import settings
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
import asyncio
import requests
import sys

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        async def twitch_api_init():
            return await Twitch(settings.APP_ID, settings.APP_SECRET)

        self.twitch = asyncio.run(twitch_api_init())
        print('Initialized Twitch API')

        if 'portal.wsgi:application' in sys.argv:
            from core.twitch_handler import TwitchHandler
            from core.helpers import data_get
            from core.models import User
            
            self.twitch_handler = TwitchHandler()
            asyncio.run(self.twitch_handler.eventsub_init())