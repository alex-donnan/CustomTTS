from .paid_action import paidAction
from tts_utils import *

import urllib
import requests

class luteAction(paidAction):
	def post_init(self):
		self.keywords = ['lute']
		self.require_next = True

	def generate(self, msg):
		if self.config['FLAGS']['clear']: return msg

		user = msg['user_name']
		output_file = f"{msg['filename']}.wav"
		message = msg['message']

		try:
			# Do lute
			url = f'https://luteboi.com/lute/?message={urllib.parse.quote_plus(message)}&key={urllib.parse.quote_plus(user)}'
			data = requests.get(url)
			with open(output_file, 'wb') as f:
				f.write(data.content)

			print(f'New file from LuteBoi: {message}: {output_file}')
			msg['filename'] = output_file
		except Exception as e:
			print(f'LuteBoi failed to generate: {e}')
		return msg