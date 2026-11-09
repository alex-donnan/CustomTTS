from .paid_action import paidAction
from piper import PiperVoice
from utilities import *
import logging
logger = logging.getLogger(__name__)
import wave

class aiAction(paidAction):
	def post_init(self):
		self.keywords = list(self.config['AI']['speakers'])
		self.regex = rf'{self.config['GENERAL']['split_text']}({'|'.join(self.keywords)})[^{self.config['GENERAL']['split_text']}]*'

	def update(self):
		self.keywords = list(self.config['AI']['speakers'])
		self.regex = rf'{self.config['GENERAL']['split_text']}({'|'.join(self.keywords)})[^{self.config['GENERAL']['split_text']}]*'
				
	def generate(self, msg):
		# generate the file
		output_file = f"{msg['filename']}.wav"
		voice = msg['message'].split(' ')[0][1:]
		message = msg['message'][len(voice)+1:]

		message = convert_numbers(message)
		message = replace_emoji(message)

		try:
			piper = PiperVoice.load(f"{self.config['AI']['samplesdir']}/{self.config['AI']['speakers'][voice]}", use_cuda=True)
			with wave.open(output_file, "wb") as file:
				piper.synthesize_wav(message, file)
				
				msg['filename'] = output_file
				logger.info(f'New file for {voice}: {message}: {output_file}')
		except Exception as e:
			logger.info(f'Failed to generate AI voice: {e}')

		return msg