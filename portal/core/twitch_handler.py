from core.actions import *
from core.models import *
from core.tasks import *
from core.helpers import MessageObject, data_set, data_get

from django.apps import apps
from django.conf import settings
from django.core.cache import cache as redis

from twitchAPI.helper import first
from twitchAPI.eventsub.webhook import EventSubWebhook
from twitchAPI.object.eventsub import ChannelFollowEvent, \
	ChannelBitsUseEvent, \
	ChannelChatMessageEvent, \
	ChannelSubscribeEvent, \
	ChannelSubscriptionGiftEvent, \
	ChannelSubscriptionMessageEvent, \
	StreamOnlineEvent, \
	StreamOfflineEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope

import os
import threading
import uuid

"""
	Twitch Handler
		- Initializes the eventsub webhook
		- Handles user authorization
		- Performs subscription for users
	
"""
class TwitchHandler():
	"""
		INITIALIZATION
	"""
	def __init__(self):
		# Create the different non-default actions
		self.actions = [
			ModeratorCommandAction(
				name='mod_command',
				description='Moderator Command'
			),
			TextToSpeechModelAction(
				name='tts_model',
				description='TTS via Trained Model'
			),
			LuteAction(
				name='lute',
				description='Lute via LuteBoi',
				key='lute'
			),

			# DEFAULT
			TextToSpeechAction(
				name='tts',
				description='Default TTS via StreamElements API'
			)
		]

		self.twitch = apps.get_app_config('core').twitch
		self.auth = UserAuthenticator(self.twitch, settings.TARGET_SCOPES, url=settings.USER_AUTH_URL)

	async def eventsub_init(self):
		self.eventsub = EventSubWebhook(settings.EVENTSUB_URL, 1501, self.twitch)
		await self.eventsub.unsubscribe_all()
		thread = threading.Thread(target=self.eventsub.start, daemon=True)
		thread.start()

		print('Initialized Webhook')

	"""
		HELPERS
	"""
	def process_message(self, event, broadcaster, chatter, message, cost):
		# Get correct message text
		if type(message) is dict:
			message = message.text

		# Split and clean on trigger
		sub_messages = message.split('#')
		while '' in sub_messages:
			sub_messages.remove('')

		for sub_message in sub_messages:
			msg = MessageObject(
				event,
				broadcaster,
				str(uuid.uuid1()),
				sub_message.strip(),
				chatter,
				cost
			)

			for action in self.actions:
				if not action.enabled: continue

				if action.validate(msg):
					generate.delay(action, msg)

		# SSE to frontend the message in question and any filenames

	"""
		EVENT DEFINITIONS
	"""
	async def on_message(self, data: ChannelChatMessageEvent):
		trigger = data_get(
			model=Trigger,
			query_params={
				'event': 'channel.chat.message'
			},
			key='trigger:channel.chat.message'
		)[0]

		if not trigger.enabled:
			print(f'Trigger of {data.subscription.type} is currently disabled globally.')
			return

		print(f'{data.event.broadcaster_user_name} : {data.event.chatter_user_name} sent a message: {data}')
		self.process_message(
			data.subscription.type,
			data.event.broadcaster_user_id,
			data.event.chatter_user_id,
			data.event.message,
			0
		)

	async def on_follow(self, data: ChannelFollowEvent):
		print(f'{data.event.broadcaster_user_name} : {data.event.user_name} now follows {data.event.broadcaster_user_name}!')

	async def on_cheer(self, data: ChannelBitsUseEvent):
		print(f'{data.event.broadcaster_user_name} : {data.event.user_name} spent bits: {data}')

	async def on_subscribe(self, data: ChannelSubscribeEvent):
		if not data.event.is_gift:
			print(f'{data.event.broadcaster_user_name} : {data.event.user_name} has subscribed.')

	async def on_subscribe_gift(self, data: ChannelSubscriptionGiftEvent):
		print(f'{data.event.broadcaster_user_name} : {data.event.user_name} gifted a subscription!')
		if not data.event.is_anonymous:
			print(f'They have gifted {data.event.cumulative_total} subs.')

	async def on_resubscribe(self, data: ChannelSubscriptionMessageEvent):
		print(f'{data.event.broadcaster_user_name} : {data.event.user_name} has resubscribed for {data.event.cumulative_months} months.')
		print(f'Message: {data.event.message.text}')

	# Listen to User stream start/end to clean up redis and save to DB
	async def on_stream_online(self, data: StreamOnlineEvent):
		print(f'{data.event.broadcaster_user_name} has started a stream.')
		user = data_get(
			model=User,
			query_params={
				'user': data.event.broadcaster_user_id
			},
			key=f'user:{data.event.broadcaster_user_id}:detail'
		)
		print(f'User {user.user} added to cache.')

		print(f'Collecting moderators for user.')
		moderators = await self.twitch.get_moderators(user.user)
		for mod in moderators:
			# Create the relevant reference, no caching
			data_set(
				model=UserModeratorRef,
				query_params={
					'user': user.user,
					'moderator': mod.user_id
				},
				model_params={
					'user': user.user,
					'moderator':mod.user_id
				},
				key=f'user:{user.user}:moderator:{mod.user_id}',
				create=True
			)

		print(f'{len(moderators)} added to cache')

	async def on_stream_offline(self, data: StreamOfflineEvent):
		print(f'{data.event.broadcaster_user_name} has ended a stream.')
		redis.delete(f'user:{data.event.broadcaster_user_id}:*')

	"""
		AUTHORIZATION AND SUBSCRIPTION
	"""
	# Subscribe to eventsub hook for user
	async def subscribe_user(self, user: User):
		print(f'Starting subscription for {user.login} to all actions.')
		await self.twitch.set_user_authentication(user.token, settings.TARGET_SCOPES, user.refresh)
		
		# Follow
		await self.eventsub.listen_channel_follow_v2(user.user, user.user, self.on_follow)
		print('Eventsub subscribed to follow.')

		# Cheer
		#await self.eventsub.listen_channel_bits_use(user.user, self.on_cheer)

		# Chat messages
		await self.eventsub.listen_channel_chat_message(user.user, user.user, self.on_message)
		print('Eventsub subscribed to chat.')

		# Subscriptions
		#await self.eventsub.listen_channel_subscribe(user.user, self.on_subscribe)
		#await self.eventsub.listen_channel_subscription_gift(user.user, self.on_subscribe_gift)
		#await self.eventsub.listen_channel_subscription_message(user.user, self.on_resubscribe)

		# Go-live
		await self.eventsub.listen_stream_online(user.user, self.on_stream_online)
		await self.eventsub.listen_stream_offline(user.user, self.on_stream_offline)
		print('Eventsub subscribed to go-live.')

		print(f'Succesfully subscribed {user.login} to all actions')

	# We should probably store the user's topic subscription ID's so we can revoke them later