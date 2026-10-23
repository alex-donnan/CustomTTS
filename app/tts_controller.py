from actions import *
from torch.backends.cuda import cuBLASModule
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

from echo import ttsEcho
from tts_websocket import ttsWebsocket
from workers import *

import configparser
import json
import os
import requests
import time
import torch.multiprocessing as mp
import uuid
import websocket

DEVMODE = False

class ttsController:
	USER_SCOPE = [
		AuthScope.BITS_READ,
		AuthScope.CHANNEL_MODERATE,
		AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
		AuthScope.USER_READ_CHAT
	]
	URI = 'https://api.twitch.tv/helix'
	WS_ENDPOINT = 'wss://eventsub.wss.twitch.tv/ws' if not DEVMODE else 'ws://127.0.0.1:8080/ws'
	SUBS_ENDPOINT = 'https://api.twitch.tv/helix/eventsub/subscriptions' if not DEVMODE else 'http://127.0.0.1:8080/eventsub/subscriptions'
	SUBSCRIPTIONS = [
		'channel.subscription.message',
		'channel.subscription.gift',
		'channel.cheer',
		'channel.chat.message'
	]

	def __init__(self):
		# config
		self.config = configparser.ConfigParser()
		self.config.read('config.ini')

		# twitch auth stuff
		self.token = None
		self.refresh_token = None
		self.reauth_window = 1
		self.reauth_last = time.time()
		self.headers = {}
		self.subscriptions = []
		self.broadcaster = {}
		self.ws_app = None

		# visual details for frontend
		self.speaker_list = eval(self.config['AI']['speakers'])
		self.sound_list = eval(self.config['SOUND']['sounds'])
		self.connected = False
		self.text_list = []

		# actions
		self.actions = {
			'SESSION': sessionStartAction(self, self.config, 'SESSION'),
			'AI': aiAction(self, self.config, 'AI'),
			'CHAT': chatAction(self, self.config, 'CHAT'),
			'LUTE': luteAction(self, self.config, 'LUTE'),
			'SOUND': soundAction(self, self.config, 'SOUND'),
			'TTS': ttsAction(self, self.config, 'TTS'),
		}

		# queues and processs for background work
		mp.set_start_method('spawn', force=True)
		self.played_file = mp.Array('c', 256)
		self.current_speaker = mp.Array('c', 256)

		self.gen_queue = mp.Queue()
		self.tts_queue = mp.Queue()
		self.gen_worker_process = genWorker(self.gen_queue, self.tts_queue, self.actions)
		self.tts_worker_process = ttsWorker(self.tts_queue, self.played_file, self.current_speaker)
		self.gen_worker_process.start()
		self.tts_worker_process.start()


		# ai controller
		self.echo = ttsEcho(self)

		# websocket server
		#self.websocket_server = ttsWebsocket()
		#def run_server():
		#	asyncio.run(self.websocket_server.start())
		#self.websocket_process = mp.Process(target=run_server, daemon=True)

	# Config
	def save_config(self):
		with open('config.ini', 'w') as configfile:
			self.config.write(configfile)

	# Shutdown
	def shutdown(self):
		self.save_config()
		self.gen_worker_process.terminate()
		self.tts_worker_process.terminate()
		#self.websocket_server.stop()
		self.echo.unload_models()

		print("Shutting down")

	# Twitch WebSocket event methods
	def on_open(self, ws):
		# update the color
		self.config.set('FLAGS', 'clear', str(False))
		print('Connected to Twitch')

	def on_message(self, ws, msg):
		self.connected = True
		msg = json.loads(msg)

		try:
			if msg['metadata']['message_type'] == 'session_welcome':
				self.actions['SESSION'].action(msg)

			if msg['metadata']['message_type'] != 'notification': return

			message_list = []
			message = msg['payload']['event']['message']
			if type(message) == dict:
				message = message['text']

			message_parts = message.split()
			last_action = None
			last_key = None
			last_ind = 0
			filename = ''

			for i, sub_message in enumerate(message_parts):
				if len(sub_message.strip()) == 0: continue

				for action in self.actions.values():
					if action == last_action and action.require_next and i-last_ind == 1: break

					key = action.validate(msg, sub_message)
					
					if bool(key):
						if last_action is None: last_action = action
						if last_key is None: last_key = key

						if last_action != action or \
							(last_key != key and key != action.default_value) or \
							key[0] == self.config['DEFAULT']['split_text']:
							msg['sub_message'] = ' '.join(message_parts[last_ind:i])
							msg_obj = last_action.action(msg)

							if bool(msg_obj):
								filename = f"{self.config['DEFAULT']['outputdir']}{uuid.uuid4()}"
								msg_obj['filename'] = filename
								message_list.append(msg_obj)

							last_action = action
							last_key = key
							last_ind = i
							break

			# final section of message
			if bool(last_action):
				msg['sub_message'] = ' '.join(message_parts[last_ind:])
				msg_obj = last_action.action(msg)

				if bool(msg_obj):
					filename = f"{self.config['DEFAULT']['outputdir']}{uuid.uuid4()}"
					msg_obj['filename'] = filename
					message_list.append(msg_obj)

			if len(message_list) > 0:
				self.text_list.append({
					'user_name': msg['payload']['event']['user_name'],
					'message': message,
					'filename': filename
				})

			self.gen_queue.put(message_list)
		except Exception as e:
			print(f'Unable to handle inbound WS message: {e}')

				
	def on_error(self, ws, msg):
		self.connected = False
		print(f'An error has occurred: {msg}')
		return

	def on_close(self, ws, close_status_code, msg):
		self.connected = False
		print(f'Closed: {close_status_code} \n - {msg}')
		return

	#Authentication
	async def update_stored_creds(self, token, refresh):
		print("Access token refreshed successfully")
		with open(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json"), 'w') as f:
			json.dump({'token': token, 'refresh': refresh}, f)

	async def auth(self):
		# Just use pre-built twitch auth
		if bool(self.config['DEFAULT']['TwitchAppId']) and bool(self.config['DEFAULT']['TwitchAppSecret']):
			twitch = await Twitch(self.config['DEFAULT']['TwitchAppId'], self.config['DEFAULT']['TwitchAppSecret'])

			auth = UserAuthenticator(twitch, ttsController.USER_SCOPE)
			self.token, self.refresh_token = await auth.authenticate()

			with open(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json"), 'w') as f:
				json.dump({'token': self.token, 'refresh': self.refresh_token}, f)
		else:
			print("Cannot run authorization")

	async def reauth(self):
		if bool(self.refresh_token):
			print("Attempting to refresh access token")

			if self.reauth_last - time.time() < self.reauth_window:
				print(f"Reauth too soon: Must be after {self.reauth_window} s")
				self.reauth_window = min(self.reauth_window * 2, 16)
			else:
				self.token, self.refresh_token = await refresh_access_token(self.refresh_token, self.config['DEFAULT']['TwitchAppId'], self.config['DEFAULT']['TwitchAppSecret'])

				self.reauth_window = 1
				self.reauth_last = time.time()
				await self.update_stored_creds(self.token, self.refresh_token)
		else:
			print("First auth not completed, trying now")
			await self.auth()

	# Run application
	async def run(self):
		# Use or generate auth
		if os.path.exists(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json")):
			# Get the broadcaster (for ID)
			with open(os.path.join(self.config['DEFAULT']['OutputDir'], "credentials.json")) as f:
				creds = json.load(f)
				self.token = creds["token"]
				self.refresh_token = creds["refresh"]

				self.headers = {
					'Authorization': f'Bearer {creds["token"]}',
					'Client-Id': self.config['DEFAULT']['TwitchAppId'],
					'Content-Type': 'application/json'
				}

				broad_request = requests.get(f"{ttsController.URI}/users?user_login={self.config['DEFAULT']['TargetChannel']}", headers=self.headers)
				self.broadcaster = broad_request.json()

		# Create the app for twitch message processing
		if not self.ws_app:
			print('Creating twitch websocket')
			websocket.setdefaulttimeout(10)
			self.ws_app = websocket.WebSocketApp(
				ttsController.WS_ENDPOINT,
				on_open=self.on_open,
				on_message=self.on_message,
				on_error=self.on_error,
				on_close=self.on_close
			)
		self.connected = True