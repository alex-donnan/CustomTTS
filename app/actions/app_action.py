from tts_utils import *

class appAction:
	def __init__(self, app, config, name):
		self.app = app
		self.config = config
		self.name = name
		self.post_init()

	def post_init(self):
		#this does nothing, only for inheritance if needed
		tooty = 'booty'

	def validate(self, msg, text):
		raise NotImplementedError("Validate not implemented")

	def action(self, msg):
		raise NotImplementedError("Action not implemented")

	def generate(self, msg):
		raise NotImplementedError("Generate not implemented")