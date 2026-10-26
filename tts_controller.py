from actions import *
from torch.backends.cuda import cuBLASModule
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

from echo import ttsEcho
from tts_websocket import ttsWebsocket
from workers import *

import ast
import configparser
import json
import os
import requests
import time
import torch
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
	SUBSCRIPTION_LIST = [
		'channel.subscription.message',
		'channel.subscription.gift',
		'channel.cheer',
		'channel.chat.message'
	]

	def __init__(self):
		mp.set_start_method("spawn", force=True)

		# config
		self.process_manager = mp.Manager()
		try:
			self.process_manager.start()
		except Exception as e:
			print('Manager already running')
		self.config_parser = configparser.ConfigParser()
		self.config_parser.read('config.ini')
		self.config = {}
		for section in self.config_parser.sections():
			self.config[section] = {}
			for key, value in self.config_parser.items(section):
				if value in ['True','False']:
					self.config[section][key] = eval(value)
				elif len(value) > 0 and value[0] == '{':
					self.config[section][key] = ast.literal_eval(value)
				else:
					self.config[section][key] = value
		
		self.config_manager = self.process_manager.dict()
		self.config_manager.update(self.config)

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
		self.connected = False
		self.device = "cuda" if torch.cuda.is_available() else "cpu"
		self.text_list = []

		# actions
		self.session_start = sessionStartAction(self, 'SESSION')
		self.actions = {
			'AI': aiAction(self.config, 'AI'),
			'CHAT': chatAction(self.config, 'CHAT'),
			'LUTE': luteAction(self.config, 'LUTE'),
			'SOUND': soundAction(self.config, 'SOUND'),
			'TTS': ttsAction(self.config, 'TTS'),
		}

		# queues and processs for background work
		mp.set_start_method('spawn', force=True)
		self.played_file = mp.Array('c', 256)
		self.current_speaker = mp.Array('c', 256)

		# workers (uninitialized)
		self.gen_queue = mp.Queue()
		self.tts_queue = mp.Queue()
		self.gen_worker_process = genWorker(self.gen_queue, self.tts_queue, self.config, self.actions)
		self.tts_worker_process = ttsWorker(self.tts_queue, self.config, self.played_file, self.current_speaker)

		# websocket server
		#self.websocket_server = ttsWebsocket()
		#def run_server():
		#	asyncio.run(self.websocket_server.start())
		#self.websocket_process = mp.Process(target=run_server, daemon=True)

	def start_workers(self):
		try:
			self.gen_worker_process.start()
			self.tts_worker_process.start()
		except Exception as e:
			print(f'Failed to start processes: {e}')

	# Config
	def save_config(self):
		try:
			with open('config.ini', 'w') as configfile:
				self.config_manager.update(self.config)
				self.config_parser.read_dict(self.config_manager)
				self.config_parser.write(configfile)
		except Exception as e:
			print(f'Failed to write config file: {e}')

	# Shutdown
	def shutdown(self):
		self.gen_worker_process.terminate()
		self.tts_worker_process.terminate()
		#self.websocket_server.stop()

		for action in self.actions.values():
			action.shutdown()

		self.save_config()
		print("Shutting down")

	# Twitch WebSocket event methods
	def on_open(self, ws):
		# update the color
		self.config['FLAGS']['clear'] = False
		print('Connected to Twitch')

	def on_message(self, ws, msg):
		msg = json.loads(msg)

		try:
			if msg['metadata']['message_type'] == 'session_welcome':
				self.session_start.action(msg)

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
				if sub_message.strip() == '': continue

				for action in self.actions.values():
					# Early escape for messages that require the next item after keyword
					if bool(last_action) and \
						action.name == last_action.name and \
						action.require_next and \
						i-last_ind == 1:
						break

					key = action.validate(msg, sub_message)

					if bool(last_action) and \
						action.default and \
						key == action.default_value and \
						last_key != key and \
						((not last_action.require_next) or (last_action.require_next and i-last_ind <=1)):
						break
					
					if bool(key):
						if last_action is None: last_action = action
						if last_key is None: last_key = key

						if last_action != action or \
							(last_key != key and key != action.default_value) or \
							key[0] == self.config['GENERAL']['split_text']:
							msg['sub_message'] = ' '.join(message_parts[last_ind:i])
							msg_obj = last_action.action(msg)

							if bool(msg_obj):
								filename = f"{self.config['GENERAL']['outputdir']}{uuid.uuid4()}"
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
					filename = f"{self.config['GENERAL']['outputdir']}{uuid.uuid4()}"
					msg_obj['filename'] = filename
					message_list.append(msg_obj)

			if len(message_list) > 0:
				self.text_list.append({
					'user_name': msg['payload']['event']['user_name'],
					'message': message,
					'filename': filename
				})

			self.gen_queue.put(message_list)
			
			# update status icon after it works
			self.connected = True
		except Exception as e:
			print(f'Unable to handle inbound WS message: {e}')
			print(f'Message: {msg}')

				
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
		with open(os.path.join(self.config['GENERAL']['outputdir'], "credentials.json"), 'w') as f:
			json.dump({'token': token, 'refresh': refresh}, f)

	async def auth(self):
		# Just use pre-built twitch auth
		if bool(self.config['GENERAL']['twitchappid']) and bool(self.config['GENERAL']['twitchappsecret']):
			twitch = await Twitch(self.config['GENERAL']['twitchappid'], self.config['GENERAL']['twitchappsecret'])

			auth = UserAuthenticator(twitch, ttsController.USER_SCOPE)
			self.token, self.refresh_token = await auth.authenticate()

			with open(os.path.join(self.config['GENERAL']['outputdir'], "credentials.json"), 'w') as f:
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
				self.token, self.refresh_token = await refresh_access_token(self.refresh_token, self.config['GENERAL']['twitchappid'], self.config['GENERAL']['twitchappsecret'])

				self.reauth_window = 1
				self.reauth_last = time.time()
				await self.update_stored_creds(self.token, self.refresh_token)
		else:
			print("First auth not completed, trying now")
			await self.auth()

	# Run application
	async def run(self):
		# Use or generate auth
		if os.path.exists(os.path.join(self.config['GENERAL']['outputdir'], "credentials.json")):
			# Get the broadcaster (for ID)
			with open(os.path.join(self.config['GENERAL']['outputdir'], "credentials.json")) as f:
				creds = json.load(f)
				self.token = creds["token"]
				self.refresh_token = creds["refresh"]

				self.headers = {
					'Authorization': f'Bearer {creds["token"]}',
					'Client-Id': self.config['GENERAL']['twitchappid'],
					'Content-Type': 'application/json'
				}

				broad_request = requests.get(f"{ttsController.URI}/users?user_login={self.config['GENERAL']['targetchannel']}", headers=self.headers)
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