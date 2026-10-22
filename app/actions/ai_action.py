from .paid_action import paidAction
from tts_utils import *

class aiAction(paidAction):
	def generate(self, msg):
		if self.config['FLAGS'].getBoolean('clear'): return msg

		output_file = f"{self.config['DEFAULT']['outputdir']}{self.generate_fname()}.wav"
		voice = msg['message'].split(' ')[0]
		message = msg['message']

		if voice in self.app.speaker_list.keys() and self.app.speaker_list[voice]['model'] in self.app.tts_synth.keys():
			message = convert_numbers(message)
			message = replace_emoji(message)

			# Generate
			self.app.tts_synth[self.app.speaker_list[voice]['model']] \
				.save_wav(self.app.tts_synth[self.app.speaker_list[voice]['model']]
					.tts(message, speaker_name=self.app.speaker_list[voice]['speaker'], language_name='en'),
					output_file
				)

			# Put the file in the play queue
			print(f'New file for {voice}: {message}: {output_file}')
			msg['filename'] = output_file
		return msg