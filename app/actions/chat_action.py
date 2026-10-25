from .app_action import appAction
from tts_utils import *

class chatAction(appAction):
	def post_inist(self):
		self.commands = {
			'!skip': (lambda: self.config['FLAGS'].update({'skip': True})),
			'!pause': (lambda: self.config['FLAGS'].update({'pause': True})),
			'!resume': (lambda: self.config['FLAGS'].update({'pause': False})),
			'!clear': (lambda: self.config['FLAGS'].update({'clear': True})),
			'!pausetts': (lambda: self.config['TTS'].update({'active': False})),
			'!resumetts': (lambda: self.config['TTS'].update({'active': True})),
			'!pauseai': (lambda: self.config['AI'].update({'active': False})),
			'!resumeai': (lambda: self.config['AI'].update({'active': True})),
			'!pauselute': (lambda: self.config['LUTE'].update({'active': False})),
			'!resumelute': (lambda: self.config['LUTE'].update({'active': True})),
			'!pausesound': (lambda: self.config['SOUND'].update({'active': False})),
			'!resumesound': (lambda: self.config['SOUND'].update({'active': True})),
		}

	def validate(self, msg, text):
		if msg['metadata']['message_type'] == 'notification' and \
			msg['payload']['subscription']['type'] == 'channel.chat.message' and \
			any(map(lambda badge: badge['set_id'] == 'moderator' or badge['set_id'] == 'broadcaster', msg['payload']['event']['badges'])) and \
			any(key in text for key in self.commands):
			return key
		return None

	def action(self, msg):
		text = msg['payload']['event']['message']['text']
		if (key in text for key in self.commands):
			self.commands[key]()

	def generate(self, msg):
		return None