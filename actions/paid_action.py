from .app_action import appAction
from tts_utils import *

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
		}
		self.post_init()

	def validate(self, msg, text) -> str | None:
		if self.config[self.name]['active'] and \
			msg['metadata']['message_type'] == 'notification' and \
			msg['payload']['subscription']['type'] != 'channel.chat.message' and \
			int(self.costs[self.event_names[msg['payload']['subscription']['type']]]) > 0 and \
			int(self.costs[self.event_names[msg['payload']['subscription']['type']]]) <= msg['payload']['subscription']['cost'] and \
			(self.default or (text[0] == self.config['GENERAL']['split_text'] and text.split(' ')[0][1:].lower() in self.keywords)):

			if self.default and text.split(' ')[0][1:].lower() not in self.keywords:
				return self.default_value
			
			return text.split(' ')[0].lower()
		return None

	def action(self, msg):
		message = {}
		if msg['payload']['subscription']['type'] == 'channel.subscription.gift':
			message = {
				'type': self.name,
				'user_name': msg['payload']['event']['user_name'],
				'message': f"{msg['payload']['event']['total']} Gifted Sub{'' if msg['payload']['event']['total'] == 1 else 's'} : {msg['sub_message']}",
				'no_message': True
			}
		elif msg['payload']['subscription']['type'] == 'channel.subscription.message':
			message = {
				'type': self.name,
				'user_name': msg['payload']['event']['user_name'],
				'message': msg['sub_message']
			}
		elif msg['payload']['subscription']['type'] == 'channel.cheer':
			message = {
				'type': self.name,
				'user_name': msg['payload']['event']['user_name'],
				'message': msg['sub_message']
			}

		message['message'] = remove_cheermotes(message['message'])

		return message