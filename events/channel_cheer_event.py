from .app_event import appEvent

class channelCheerEvent(appEvent):
	@staticmethod
	def get_type():
		return 'channel.cheer'

	@staticmethod
	def get_user(msg):
		return msg['payload']['event']['user_name']

	@staticmethod
	def get_cost(msg):
		return msg['payload']['event']['bits']

	@staticmethod
	def get_text(msg):
		return msg['payload']['event']['message']