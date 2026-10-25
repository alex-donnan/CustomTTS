from .paid_action import paidAction
from tts_utils import *

class aiAction(paidAction):
	def __init__(self, config, name, echo):
		super().__init__(config, name)
		self.echo = echo

	def generate(self, msg):
		if not bool(self.echo):
			self.app.config['AI']['active'] = False
			return msg

		# check that echo is updated
		for key in self.echo.speaker_audio.keys():
			if key in self.app.config['AI']['speakers'] and key not in self.echo.speaker_audio:
				self.echo.add_speaker(key, self.app.config['AI']['speakers'][key])
			elif key not in self.app.config['AI']['speakers'] and key in self.echo.speaker_audio:
				self.echo.remove_speaker(key)

		# generate the file
		output_file = f"{msg['filename']}.wav"
		voice = msg['message'].split(' ')[0][1:]
		message = msg['message']

		if voice not in self.echo.speaker_audio.keys():
			message = convert_numbers(message)
			message = replace_emoji(message)

			if self.echo.generate(voice, message, output_file):
				print(f'New file for {voice}: {message}: {output_file}')
				msg['filename'] = output_file
			else:
				print(f'Echo failed to generate')
		return msg