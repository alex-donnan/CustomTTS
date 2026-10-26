from .app_action import appAction
from tts_utils import *

import os
import requests

class sessionStartAction(appAction):
	def validate(self, msg, text=""):
		return msg['metadata']['message_type'] == 'session_welcome'

	def action(self, msg):
		# session variables
		session_id = msg['payload']['session']['id']

		init_check = requests.get(
			self.app.SUBS_ENDPOINT,
			params = { 'status':'enabled' },
			headers=self.app.headers
		).json()

		if 'error' in init_check:
			print(f"Initializing failed, {init_check['error']}: {init_check['message']}")
			if init_check['message'] == 'Invalid OAuth token':
				print('Attempting fix for "Invalid OAuth token"... removing stored credentials')
				os.remove(os.path.join(self.app.config['GENERAL']['outputdir'], "credentials.json"))

			raise Exception(init_check['message'])

		sub_check = [sub['type'] for sub in init_check['data']]

		for sub in self.app.subscriptions:
			if sub not in sub_check:
				self.app.subscriptions.remove(sub)

		for sub_type in self.app.SUBSCRIPTION_LIST:
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
				self.app.subscriptions.append(sub_type)
				print(f'Subscription response: {response.json()}')

		return None

	def generate(self, msg):
		return None