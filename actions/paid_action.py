from .app_action import appAction
from tts_utils import *
import events

import logging
logger = logging.getLogger(__name__)
import re

class paidAction(appAction):
	keywords = []

	def __init__(self, config, name):
		self.config = config
		self.name = name
		self.costs = self.config[self.name]['costs']
		self.event_names = {
			'channel.subscription.gift': 'subscriptions',
			'channel.subscription.message': 'subscriptions',
			'channel.cheer': 'bits',
			'channel.channel_points_custom_reward_redemption.update': 'points',
		}
		self.post_init()

	def update(self):
		# inheritance
		return

	def validate(self, msg, text) -> str | None:
		self.update()

		matches = list(re.finditer(self.regex, text, re.IGNORECASE))
		type = msg['payload']['subscription']['type']
		cost = 0
		if hasattr(events, '__all__'):
			for event in events.__all__:
				if event.get_type() == type:
					cost = event.get_cost(msg)
					break

		if type in self.event_names and \
			self.config[self.name]['active'] and \
			int(self.costs[self.event_names[type]]) > 0 and \
			int(self.costs[self.event_names[type]]) <= cost and \
			len(matches) > 0:
			return matches

		return []

	def action(self, msg):
		message = {}

		user = ''
		text = ''
		cost = 0
		if hasattr(events, '__all__'):
			for event in events.__all__:
				if event.get_type() == type:
					user = event.get_user(msg)
					text = event.get_text(msg)
					cost = event.get_cost(msg)
					break

		if msg['payload']['subscription']['type'] == 'channel.subscription.gift':
			message = {
				'type': self.name,
				'user_name': user,
				'message': f"{cost} Gifted Sub{'' if cost == 1 else 's'} : {msg['sub_message']}",
				'no_message': True
			}
		else:
			message = {
				'type': self.name,
				'user_name': user,
				'message': msg['sub_message']
			}

		message['message'] = remove_cheermotes(message['message'])

		return message