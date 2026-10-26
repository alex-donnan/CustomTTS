from .paid_action import paidAction
from tts_utils import *
import logging
logger = logging.getLogger(__name__)

class aiAction(paidAction):
	def post_init(self):
		self.echo = None
		self.keywords = list(self.config['AI']['speakers'])
		self.regex = rf'{self.config['GENERAL']['split_text']}({'|'.join(self.keywords)})[^{self.config['GENERAL']['split_text']}]*'

	def update(self):
		self.keywords = list(self.config['AI']['speakers'])
		self.regex = rf'{self.config['GENERAL']['split_text']}({'|'.join(self.keywords)})[^{self.config['GENERAL']['split_text']}]*'

	def generate(self, msg):
		if not bool(self.echo):
			self.config['AI']['active'] = False
			return msg

		# check that echo is updated
		for key in self.echo.speaker_audio.keys():
			if key in self.config['AI']['speakers'] and key not in self.echo.speaker_audio:
				self.echo.add_speaker(key, self.config['AI']['speakers'][key])
			elif key not in self.config['AI']['speakers'] and key in self.echo.speaker_audio:
				self.echo.remove_speaker(key)

		# generate the file
		output_file = f"{msg['filename']}.wav"
		voice = msg['message'].split(' ')[0][1:]
		message = msg['message'][len(voice)+1:]

		if voice in self.echo.speaker_audio.keys():
			message = convert_numbers(message)
			message = replace_emoji(message)

			if self.echo.generate(voice, message, output_file):
				logger.info(f'New file for {voice}: {message}: {output_file}')
				msg['filename'] = output_file
			else:
				logger.info(f'Echo failed to generate')
		return msg