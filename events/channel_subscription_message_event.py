from .app_event import appEvent

class channelSubscriptionMessageEvent(appEvent):
	@staticmethod
	def get_type():
		return 'channel.subscription.message'

	@staticmethod
	def get_user(msg):
		return msg['payload']['event']['user_name']

	@staticmethod
	def get_cost(msg):
		return msg['payload']['event']['duration_months']

	@staticmethod
	def get_text(msg):
		return msg['payload']['event']['message']['text']