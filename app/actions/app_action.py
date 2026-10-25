from tts_utils import *

class appAction:
	loaded = True
	require_next = False

	def __init__(self, app, name):
		self.app = app
		self.name = name
		self.post_init()

	def post_init(self):
		#this is for inheritance
		return

	def is_loaded(self):
		return self.loaded

	def lazy_load(self):
		#this is for inheritance
		return

	def validate(self, msg, text):
		raise NotImplementedError("Validate not implemented")

	def action(self, msg):
		raise NotImplementedError("Action not implemented")

	def generate(self, msg):
		raise NotImplementedError("Generate not implemented")

	def shutdown(self):
		#this is for inheritance
		return