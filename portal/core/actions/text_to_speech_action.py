from core.actions import BaseAction
from core.helpers import MessageObject, data_get
from django.conf import settings
import requests

"""
	Text To Speech (standard) via StreamElements API

	This is the default for any messages that do not have explicit commands
"""
class TextToSpeechAction(BaseAction):
	voices = {
		'brian': 'Brian',
		'ivy': 'Ivy',
		'kimberly': 'Kimberly',
		'joey': 'Joey',
		'mizuki': 'Mizuki',
		'chantal': 'Chantal',
		'mathieu': 'Mathieu',
		'maxim': 'Maxim',
		'hans': 'Hans',
		'raveena': 'Raveena'
	}

	def validate(self, msg: MessageObject) -> bool:
		user_setting = data_get(
			model=UserSetting,
			query_params={
				'user': msg.broadcaster,
				'action_type': self.name,
				'trigger_type': msg.event
			},
			key=f'user:{msg.broadcaster}:setting:{self.name}:{msg.event}',
			ttl=60
		)
		
		return user_setting[0].enabled

	def generate(self, msg: MessageObject):
		try:
			voice = self.voices.get(msg.message.split()[0])
			if voice is None:
				voice = 'Brian'

			data = requests.get(
				'https://api.streamelements.com/kappa/v2/speech',
				params={
					'voice': voice,
					'text': msg.message
				}
			)
			
			with open(f'{settings.TMP_FILE_PATH}/{msg.file_name}.mp3', 'wb') as f:
				f.write(data.content)

			# We're writing the file but need to alert the page for pickup SSE
		except Exception as ex:
			print(f'Generation of TTS message failed: {ex}')

			# Looks like gen failed, alert the page
		