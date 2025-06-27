from django.conf import settings
from models import User
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from twitchAPI.eventsub.webhook import EventSubWebhook
from twitchAPI.object.eventsub import ChannelFollowEvent, \
	ChannelBitsUseEvent, \
	ChannelChatMessageEvent, \
	ChannelSubscribeEvent, \
	ChannelSubscriptionGiftEvent, \
	ChannelSubscriptionMessageEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
import asyncio
import redis

# Our Twitch Listener class is a listener
class TwitchListener():
	twitch: Twitch | None = None
	eventsub: EventSubWebhook | None = None
	channels: dict = {}

	# Set App and Eventsub
	async def run(self):
		self.twitch = await Twitch(settings.APP_ID, settings.APP_SECRET)

		eventsub = EventSubWebhook(settings.EVENTSUB_URL, 1502, self.twitch)
		await eventsub.unsubscribe_all()
		eventsub.start()

	# Event definitions
	async def on_message(self, data: ChannelChatMessageEvent):
		print(f'{data.event.chatter_user_name} sent a message: {data}')
		if data.event.chatter_user_id in 

	async def on_follow(self, data: ChannelFollowEvent):
		# our event happened, lets do things with the data we got!
		print(f'{data.event.user_name} now follows {data.event.broadcaster_user_name}!')

	async def on_cheer(self, data: ChannelBitsUseEvent):
		print(f'{data.event.user_name} spent bits: {data}')

	async def on_subscribe(self, data: ChannelSubscribeEvent):
		if not data.event.is_gift:
			print(f'{data.event.user_name} has subscribed.')

	async def on_subscribe_gift(self, data: ChannelSubscriptionGiftEvent):
		print(f'{data.event.user_name} gifted a subscription!')
		if not data.event.is_anonymous:
			print(f'They have gifted {data.event.cumulative_total} subs.')

	async def on_resubscribe(self, data: ChannelSubscriptionMessageEvent):
		print(f'{data.event.user_name} has resubscribed for {data.event.cumulative_months} months.')
		print(f'Message: {data.event.message.text}')

	# Authorize a new user
	async def authorize_user(self, user: User):
		if self.twitch == None:
			print('Twitch App must be initialized')
			return

		auth_user = await first(self.twitch.get_users(user_ids=user.user_id))
		auth = UserAuthenticator(self.twitch, settings.TARGET_SCOPES)
		await auth.authenticate()

		# Under the assumption of the User being the streamer
		self.channels[user.]

	# Subscribe to eventsub hook for user
	async def subscribe_user(self, user: User, sub_scope: list[AuthScope] = settings.TARGET_SCOPES):
		if self.eventsub == None:
			print('EventSub must be initialized')
			return

		for scope in sub_scope:
			if scope == 'MODERATOR_READ_FOLLOWERS':
				await self.eventsub.listen_channel_follow_v2(user.user_id, user.user_id, self.on_follow)
			if scope == 'BITS_READ':
				await self.eventsub.listen_channel_bits_use(user.user_id, self.on_cheer)
			if scope == 'USER_READ_CHAT':
				await self.eventsub.listen_channel_chat_message(user.user_id, user.user_id, self.on_message)
			if scope == 'CHANNEL_READ_SUBSCRIPTIONS':
				await self.eventsub.listen_channel_subscribe(user.user_id, self.on_subscribe)
				await self.eventsub.listen_channel_subscription_gift(user.user_id, self.on_subscribe_gift)
				await self.eventsub.listen_channel_subscription_message(user.user_id, self.on_resubscribe)