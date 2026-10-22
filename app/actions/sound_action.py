from .paid_action import paidAction
from tts_utils import *

import os
import requests
import shutil

class soundAction(paidAction):
	def generate(self, msg):
		if self.config['FLAGS']['clear']: return msg

		voice = msg['message'].split(' ')[0]
		output_file = f"{self.config['DEFAULT']['outputdir']}{self.generate_fname()}.wav"
		
		# Dear god forgive me for this sin
		if voice in self.app.sound_list:
			shutil.copy(os.path.join(self.config['DEFAULT']['assetdir'], self.app.sound_list[voice]), output_file)

			#Put the file in the play queue
			print(f'New file for {voice}: { msg["message"]}: {output_file}')
			msg['filename'] = output_file

		return msg