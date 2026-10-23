from .paid_action import paidAction
from tts_utils import *

import os
import requests
import shutil

class soundAction(paidAction):
	def post_init(self):
		self.keywords = list(self.app.sound_list)

	def generate(self, msg):
		if not self.config[self.name].getboolean('active'): return msg

		output_file =  f"{msg['filename']}.wav"
		sound = msg['message'].split(' ')[0][1:].lower()
		
		# Dear god forgive me for this sin
		try:
			shutil.copy(os.path.join(self.config['SOUND']['soundsdir'], self.app.sound_list[sound]), output_file)

			#Put the file in the play queue
			print(f'New file for {sound}: { msg["message"]}: {output_file}')
			msg['filename'] = output_file
		except Exception as e:
			print(f'Sound failed to pass to file: {e}')

		return msg