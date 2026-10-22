from .paid_action import paidAction
from tts_utils import *

import requests
import urllib

class ttsAction(paidAction):
	default = True
	voices = {
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
	keywords = voices.keys()

	def generate(self, msg):
		if self.config['FLAGS'].getboolean('clear'): return msg

		output_file = f"{self.config['DEFAULT']['outputdir']}{self.generate_fname()}.mp3"
		voice = msg['message'].split(' ')[0]
		if voice in self.keywords:
			voice = self.voices[voice]
		else:
			voice = 'Brian'
		message = msg['message']

		# Do Brian
		url = f"https://api.streamelements.com/kappa/v2/speech?voice={urllib.parse.quote(voice)}&text={urllib.parse.quote(message)}&key={self.config[self.name]['streamelementskey']}"
		data = requests.get(url)
		with open(output_file, 'wb') as f:
			f.write(data.content)

		# Put the file in the play queue
		print(f'New file for {voice}: {message}: {output_file}')
		msg['filename'] = output_file

		return msg