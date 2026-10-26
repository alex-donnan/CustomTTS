from .paid_action import paidAction
from tts_utils import *

import logging
logger = logging.getLogger(__name__)
import requests

class ttsAction(paidAction):
	def post_init(self):
		self.default = True
		self.default_value = 'brian'
		self.voices = {
			'brian': 'Brian',
			'ivy': 'Ivy',
			'kimberly': 'Kimberly',
			'joey': 'Joey',
			'mizuki': 'Mizuki',
			'chantal': 'Chantal',
			'mathieu': 'Mathieu',
			'matthew': 'Mathieu',
			'maxim': 'Maxim',
			'hans': 'Hans',
			'raveena': 'Raveena'
		}
		self.keywords = self.voices.keys()
		self.regex = rf'{self.config['GENERAL']['split_text']}({'|'.join(self.keywords)})[^{self.config['GENERAL']['split_text']}]*'

	def generate(self, msg):
		output_file = f"{msg['filename']}.mp3"
		voice = msg['message'].split(' ')[0][1:].lower()
		message = msg['message']
		if voice in self.keywords:
			voice = self.voices[voice]
			message = msg['message'][len(voice)+1:]
		else:
			voice = 'Brian'

		try:
			# Do Brian
			url = "https://api.streamelements.com/kappa/v2/speech"
			data = requests.get(url, params={
				'voice': voice,
				'text': message,
				'key': self.config['TTS']['streamelementskey']
			})

			with open(output_file, 'wb') as f:
				f.write(data.content)

			# Put the file in the play queue
			logger.info(f'New file for {voice}: {message}: {output_file}')
			msg['filename'] = output_file
		except Exception as e:
			logger.warn(f'TTS failed to generate: {e}')

		return msg