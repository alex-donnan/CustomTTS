from core.actions import BaseAction
from core.models import UserSetting
from core.helpers import MessageObject

"""
	Text to Speech using a trained model
"""
class TextToSpeechModelAction(BaseAction):
	def validate(self, msg: MessageObject) -> bool:
		user_setting = UserSetting.objects.filter(user=msg.broadcaster, action_type=self.name).first()
			
		return False

	def generate(self, msg: MessageObject):
		# TTS generation by voice
		# This MUST be specific to user outside of predefined voices (David?)
		
		# We're writing the file but need to alert the page for pickup SSE
		print('butt')