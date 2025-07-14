from core.actions import BaseAction
from core.helpers import MessageObject, data_get, data_set
from core.models import UserModeratorRef

"""
	Moderator Commands
"""
class ModeratorCommandAction(BaseAction):
	def skip_message(self, broadcaster: str):
		print('skipping message')
		# This will send an SSE to the broadcaster's page

	def pause_tts(self, broadcaster: str):
		print('pause tts')
		# This will send an SSE to the broadcaster's page

		tts_setting = data_get(
			model=UserSetting,
			query_params={
				'user': broadcaster,
				'action_type': 'tts'
			},
			key=f'user:{broadcaster}:setting:tts:*',
			ttl=60
		)
		tts_model_setting = data_get(
			model=UserSetting,
			query_params={
				'user': broadcaster,
				'action_type': 'tts_model'
			},
			key=f'user:{broadcaster}:setting:tts_model:*',
			ttl=60
		)

	def pause_lute(self, broadcaster: str):
		print('pause lute')
		# This will send an SSE to the broadcaster's page

		lute_setting = data_get(
			model=UserSetting,
			query_params={
				'user': broadcaster,
				'action_type': 'lute'
			},
			key=f'user:{broadcaster}:setting:lute:*',
			ttl=60
		)

	def pause(self, broadcaster: str):
		print('pause all')
		# This will send an SSE to the broadcaster's page

		self.pause_tts(broadcaster)
		self.pause_lute(broadcaster)

	def play_tts(self, broadcaster: str):
		print('play tts')
		# This will send an SSE to the broadcaster's page

		tts_setting = data_get(
			model=UserSetting,
			query_params={
				'user': broadcaster,
				'action_type': 'tts'
			},
			key=f'user:{broadcaster}:setting:tts:*',
			ttl=60
		)
		tts_model_setting = data_get(
			model=UserSetting,
			query_params={
				'user': broadcaster,
				'action_type': 'tts_model'
			},
			key=f'user:{broadcaster}:setting:tts_model:*',
			ttl=60
		)

	def play_lute(self, broadcaster: str):
		print('play lute')
		# This will send an SSE to the broadcaster's page

		lute_setting = data_get(
			model=UserSetting,
			query_params={
				'user': broadcaster,
				'action_type': 'lute'
			},
			key=f'user:{broadcaster}:setting:lute:*',
			ttl=60
		)

	def play(self, broadcaster: str):
		print('play')
		# This will send an SSE to the broadcaster's page

		self.play_tts(broadcaster)
		self.play_lute(broadcaster)

	def clear(self, broadcaster: str):
		print('clear messages')
		# This will send an SSE to the broadcaster's page

	commands = {
		'!skip': skip_message,
		'!pause': pause,
		'!pause_tts': pause_tts,
		'!pause_lute': pause_lute,
		'!play': play,
		'!play_tts': play_tts,
		'!play_lute': play_lute,
		'!clear': clear
	}

	def validate(self, msg: MessageObject) -> bool:
		user_setting = data_get(
			model=UserSetting,
			query_params={
				'user': msg.broadcaster,
				'action_type': self.name
			},
			key=f'user:{msg.broadcaster}:setting:{self.name}:{msg.event}',
			ttl=60
		)
		if len(user_setting) == 0: return False
		if not user_setting[0].enabled: return False

		moderators = data_get(
			model=UserModeratorRef,
			query_params={
				'user': msg.broadcaster,
				'moderator': msg.user
			},
			key=f'user:{msg.broadcaster}:moderator:{msg.user}',
			ttl=60
		)
		if len(moderators) == 0: return False

		# Are any commands in the message
		for command in self.commands.keys():
			if command in msg.message:
				return True

		return False

	def generate(self, msg: MessageObject):
		for command in self.commands.keys():
			if command in msg.message:
				self.commands[command](self, msg.broadcaster)