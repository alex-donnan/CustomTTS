from numpy import outer

from .paid_action import paidAction
from tts_utils import *

import shutil
import requests

class luteAction(paidAction):
	def generate(self, msg):
		if self.config['FLAGS'].getboolean('clear'): return msg

		user = msg['user_name']
		output_file = f"{self.config['DEFAULT']['outputdir']}{self.generate_fname()}.wav"
		message = msg['message']

		# Do lute
		url = f'https://luteboi.com/lute/?message={urllib.parse.quote_plus("#lute " + message)}&key={urllib.parse.quote_plus(user)}'
		data = requests.get(url)
		with open(output_file, 'wb') as f:
			f.write(data.content)

		msg['filename'] = output_file
		return msg