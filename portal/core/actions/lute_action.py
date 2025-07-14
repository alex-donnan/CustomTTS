from core.actions import BaseAction
from core.helpers import MessageObject, data_get
from django.conf import settings
import requests

"""
	Luting via LuteBoi
"""
class LuteAction(BaseAction):
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
		if len(user_setting) == 0: return False
		
		return user_setting[0].enabled and msg.message.split()[0] == self.key

	def generate(self, msg: MessageObject):
		try:
			data = requests.get(
				'https://luteboi.com/lute/',
				params={
					'message': f'#lute {msg.message}',
					'key': msg.user
				}
			)
			
			with open(f'{settings.TMP_FILE_PATH}/{msg.file_name}.wav', 'wb') as f:
				f.write(data.content)
		except Exception as ex:
			print(f'Generation of lute message broke: {ex}')	
		
		# We're writing the file but need to alert the page for pickup SSE