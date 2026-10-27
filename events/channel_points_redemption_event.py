from .app_event import appEvent

class channelPointsRedemptionEvent(appEvent):
	@staticmethod
	def get_type():
		return 'channel.channel_points_custom_reward_redemption.update'

	@staticmethod
	def get_user(msg):
		return msg['payload']['event']['user_name']

	@staticmethod
	def get_cost(msg):
		return msg['payload']['event']['reward']['cost'] if msg['payload']['event']['status'] == 'fulfilled' else 0

	@staticmethod
	def get_text(msg):
		return msg['payload']['event']['user_input']