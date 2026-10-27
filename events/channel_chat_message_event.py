from .app_event import appEvent

class channelChatMessageEvent(appEvent):
	@staticmethod
	def get_type():
		return 'channel.chat.message'

	@staticmethod
	def get_user(msg):
		return msg['payload']['event']['chatter_user_name']

	@staticmethod
	def get_cost(msg):
		return 0 #no cost

	@staticmethod
	def get_text(msg):
		return msg['payload']['event']['message']['text']