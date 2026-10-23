from .app_action import appAction
from tts_utils import *

class paidAction(appAction):
	default = False
	default_value = ''
	keywords = []

	def __init__(self, app, config, name):
		self.app = app
		self.config = config
		self.name = name
		self.costs = eval(self.config[self.name]['costs'])
		self.event_costs = {
			'channel.subscription.gift': self.costs['subscriptions'],
			'channel.subscription.message': self.costs['subscriptions'],
			'channel.cheer': self.costs['bits'],
		}
		self.post_init()

	def validate(self, msg, text) -> str | None:
		if msg['metadata']['message_type'] == 'notification' and \
			msg['payload']['subscription']['type'] != 'channel.chat.message' and \
			self.event_costs[msg['payload']['subscription']['type']] <= msg['payload']['subscription']['cost'] and \
			(self.default or (text[0] == self.config['DEFAULT']['split_text'] and text.split(' ')[0][1:].lower() in self.keywords)):

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