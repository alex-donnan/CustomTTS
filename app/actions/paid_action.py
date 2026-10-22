from .app_action import appAction
from tts_utils import *

class paidAction(appAction):
	default = False
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

	def validate(self, msg, text):
		if not self.config[self.name].getboolean('active'): return False

		if msg['metadata']['message_type'] == 'notification' and \
			msg['payload']['subscription']['type'] != 'channel.chat.message' and \
			self.event_costs[msg['payload']['subscription']['type']] <= msg['payload']['subscription']['cost'] and \
			(self.default or text.split(' ')[0] in self.keywords):
			return True
		return False

	def action(self, msg):
		message = {}
		if msg['payload']['subscription']['type'] == 'channel.subscription.gift':
			message = {
				'type': self.name,
				'user_name': msg['payload']['event']['user_name'],
				'message': f"{msg['payload']['event']['total']} Gifted Sub{'' if msg['payload']['event']['total'] == 1 else 's'}",
				'no_message': True
			}
		elif msg['payload']['subscription']['type'] == 'channel.subscription.message':
			message = {
				'type': self.name,
				'user_name': msg['payload']['event']['user_name'],
				'message': msg['payload']['event']['message']['text']
			}
		elif msg['payload']['subscription']['type'] == 'channel.cheer':
			message = {
				'type': self.name,
				'user_name': msg['payload']['event']['user_name'],
				'message': msg['payload']['event']['message']
			}

		message['message'] = remove_cheermotes(message['message'])

		return message