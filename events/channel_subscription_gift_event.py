from .app_event import appEvent

class channelSubscriptionGiftEvent(appEvent):
	@staticmethod
	def get_type():
		return 'channel.subscription.gift'

	@staticmethod
	def get_user(msg):
		return msg['payload']['event']['user_name']

	@staticmethod
	def get_cost(msg):
		return msg['payload']['event']['total']

	@staticmethod
	def get_text(msg):
		return ''