from .paid_action import paidAction
from tts_utils import *

import logging
logger = logging.getLogger(__name__)
import urllib
import requests

class luteAction(paidAction):
	def post_init(self):
		self.keywords = ['lute']
		self.regex = rf'{self.config['GENERAL']['split_text']}lute (m |\d+ )?\S*'
		self.max_length = 3

	def generate(self, msg):
		user = msg['user_name']
		output_file = f"{msg['filename']}.wav"
		message = msg['message']

		# luteboi requires hash notation
		if message[0] != '#':
			message = f'#{message[1:]}'

		try:
			# Do lute
			url = f'https://luteboi.com/lute/?message={urllib.parse.quote_plus(message)}&key={urllib.parse.quote_plus(user)}'
			data = requests.get(url)
			with open(output_file, 'wb') as f:
				f.write(data.content)

			logger.info(f'New file from LuteBoi: {message}: {output_file}')
			msg['filename'] = output_file
		except Exception as e:
			logger.warn(f'LuteBoi failed to generate: {e}')
		return msg