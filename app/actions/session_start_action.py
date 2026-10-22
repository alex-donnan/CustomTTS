from .app_action import appAction
from tts_utils import *

import requests

class sessionStartAction(appAction):
	def validate(self, msg, text=""):
		print("Valid session")
		return msg['metadata']['message_type'] == 'session_welcome'

	def action(self, msg):
		print("action sessions")
		# session variables
		session_id = msg['payload']['session']['id']

		init_check = requests.get(self.app.SUBS_ENDPOINT + '?status=enabled', headers=self.app.headers).json()
		sub_check = [sub['type'] for sub in init_check['data']]
		print(f'Previous subscriptions that are active: {sub_check}\nThese will be skipped')

		for sub in self.app.subscriptions:
			if sub not in sub_check:
				self.app.subscriptions.remove(sub)

		for sub_type in self.app.SUBSCRIPTIONS:
			if sub_type not in self.app.subscriptions:
				sub_data = {
					'type': sub_type,
					'version': '1',
					'condition': {
						'broadcaster_user_id': self.app.broadcaster['data'][0]['id'],
						'user_id': self.app.broadcaster['data'][0]['id']
					},
					'transport': {
						'method': 'websocket',
						'session_id': session_id
					}
				}

				response = requests.post(self.app.SUBS_ENDPOINT, json=sub_data, headers=self.app.headers)
				self.app.subscriptions.append(sub_type);
				print(f'Subscription response: {response.json()}')

		return None

	def generate(self, msg):
		return None