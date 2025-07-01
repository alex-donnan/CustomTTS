from django.apps import AppConfig
import asyncio

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from core.twitch.listener import TwitchListener
        
        self.twitch_listener = TwitchListener()
        asyncio.run(self.twitch_listener.init())