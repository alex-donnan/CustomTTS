from .paid_action import paidAction
from tts_utils import *

class aiAction(paidAction):
	def post_init(self):
		self.keywords = list(self.app.speaker_list)

	def generate(self, msg):
		if not self.config[self.name].getboolean('active'): return msg

		output_file = f"{self.config['DEFAULT']['outputdir']}{self.generate_fname()}.wav"
		voice = msg['message'].split(' ')[0][1:]
		message = msg['message']

		if voice not in self.app.echo.speaker_audio.keys():
			message = convert_numbers(message)
			message = replace_emoji(message)

			if self.app.echo.generate(voice, message, output_file):
				print(f'New file for {voice}: {message}: {output_file}')
				msg['filename'] = output_file
			else:
				print(f'Echo failed to generate')
		return msg