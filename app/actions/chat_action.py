from .app_action import appAction
from tts_utils import *

class chatAction(appAction):
	def __init__(self, app, config):
		self.app = app
		self.config = config
		self.commands = {
			'!skip': (lambda: self.app.config.set('FLAGS', 'skip', str(True))),
			'!pause': (lambda: self.app.config.set('FLAGS', 'pause', str(True))),
			'!resume': (lambda: self.app.config.set('FLAGS', 'pause', str(False))),
			'!clear': (lambda: self.app.config.set('FLAGS', 'clear', str(True))),
			'!pausetts': (lambda: self.app.config.set('TTS', 'active', str(False))),
			'!resumetts': (lambda: self.app.config.set('TTS', 'active', str(True))),
			'!pauseai': (lambda: self.app.config.set('AI', 'active', str(False))),
			'!resumeai': (lambda: self.app.config.set('AI', 'active', str(True))),
			'!pauselute': (lambda: self.app.config.set('LUTE', 'active', str(False))),
			'!resumelute': (lambda: self.app.config.set('LUTE', 'active', str(True))),
			'!pausesound': (lambda: self.app.config.set('SOUND', 'active', str(False))),
			'!resumesound': (lambda: self.app.config.set('SOUND', 'active', str(True)))
		}

	def validate(self, msg, text):
		if not self.config['CHAT'].getboolean('active'): return False

		if msg['metadata']['message_type'] == 'notification' and \
			msg['payload']['subscription']['type'] == 'channel.chat.message' and \
			msg['payload']['event']['message_type'] == 'text' and \
			any(map(lambda badge: badge['set_id'] == 'moderator' or badge['set_id'] == 'broadcaster', msg['payload']['event']['badges'])) and \
			f"!{text.split(' ')[0]}" in self.commands.keys():
			return True
		return False

	def action(self, msg):
		fn = self.commands.get(msg['payload']['event']['message']['text'].split(' ')[0])
		if fn:
			fn()
			self.app.save_config()

	def generate(self, msg):
		print("I don't do anything!")
		return None