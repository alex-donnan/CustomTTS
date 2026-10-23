from tts_utils import *

import os
import uuid

class appAction:
	def __init__(self, app, config, name):
		self.app = app
		self.config = config
		self.name = name
		self.post_init()

	def post_init(self):
		#this does nothing, only for inheritance if needed
		hello = 'world'

	def validate(self, msg, text):
		raise NotImplementedError("Validate not implemented")

	def action(self, msg):
		raise NotImplementedError("Action not implemented")

	def generate(self, msg):
		raise NotImplementedError("Generate not implemented")

	def generate_fname(self):
		fname = uuid.uuid4()
		# In the highly unlikely event it exists already, recurse
		if os.path.exists(os.path.join(self.config['DEFAULT']['outputdir'], f'{fname}.wav')):
			fname = uuid.uuid4()
		return fname