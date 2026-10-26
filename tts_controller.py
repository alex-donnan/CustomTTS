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
import logging
logger = logging.getLogger(__name__)
import os
import requests
import shutil
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

		# check config exists
		if not os.path.exists('config.ini'):
			if os.path.exists('config.ini.example'):
				shutil.copy('config.ini.example', 'config.ini')
			else:
				raise Exception('Config example file missing, aborting')

		# config
		self.process_manager = mp.Manager()
		try:
			self.process_manager.start()
		except Exception as e:
			logger.warn('Manager already running')
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

		# check all paths exist
		if not os.path.exists(self.config['GENERAL']['outputdir']): os.mkdir(self.config['GENERAL']['outputdir'])
		if not os.path.exists(self.config['GENERAL']['modeldir']): os.mkdir(self.config['GENERAL']['modeldir'])
		if not os.path.exists(self.config['GENERAL']['assetsdir']): os.mkdir(self.config['GENERAL']['assetsdir'])
		if not os.path.exists(self.config['AI']['samplesdir']): os.mkdir(self.config['AI']['samplesdir'])
		if not os.path.exists(self.config['SOUND']['soundsdir']): os.mkdir(self.config['SOUND']['soundsdir'])

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
			'DEFAULT': ttsAction(self.config, 'TTS'),
		}

		# queues and processs for background work
		mp.set_start_method('spawn', force=True)
		self.played_file = mp.Array('c', 256)
		self.current_speaker = mp.Array('c', 256)

		# workers (uninitialized)
		self.gen_queue = mp.Queue()
		self.tts_queue = mp.Queue()
		self.gen_worker_process = genWorker(self.gen_queue, self.tts_queue, self.config_manager, self.actions)
		self.tts_worker_process = ttsWorker(self.tts_queue, self.config_manager, self.played_file, self.current_speaker)

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
			logger.warn(f'Failed to start processes: {e}')

	# Config
	def save_config(self):
		try:
			with open('config.ini', 'w') as configfile:
				self.config_manager.update(self.config)
				self.config_parser.read_dict(self.config_manager)
				self.config_parser.write(configfile)
		except Exception as e:
			logger.warn(f'Failed to write config file: {e}')

	# Shutdown
	def shutdown(self):
		self.gen_worker_process.terminate()
		self.tts_worker_process.terminate()
		#self.websocket_server.stop()

		for action in self.actions.values():
			action.shutdown()

		self.save_config()
		logger.info("Shutting down")

	# Twitch WebSocket event methods
	def on_open(self, ws):
		# update the color
		self.config['FLAGS']['clear'] = False
		logger.info('Connected to Twitch')

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
			message = message.strip()

			action_data = {}
			for action in self.actions.values():
				action_data[action.name] = action.validate(msg, message)

			# we're getting match data back from action validation
			# we need to insert and sort the actions
			matches = []
			for key in action_data.keys():
				if bool(action_data[key]):
					for data in action_data[key]:
						data = {
							'key': key,
							'start': data.start(),
							'end': data.end(),
							'text': data.group()
						}
						matches.append(data)
			matches.sort(key=lambda data: data['start'])

			# next default action to missing sections
			matches_final = matches[:]
			for i, match in enumerate(matches):
				if i == 0 and match['start'] > 0:
					matches_final.insert(0, {
						'key': 'DEFAULT',
						'start': 0,
						'end': match['start'],
						'text': message[:match['start']]
					})
				if match['start'] - matches[max(0,i-1)]['end'] > 1:
					match_ind = next((j for j, el in enumerate(matches_final) if el['start'] == match['start']))
					matches_final.insert(match_ind, {
						'key': 'DEFAULT',
						'start': matches[i-1]['end'],
						'end': match['start'],
						'text': message[matches[i-1]['end']:match['start']]
					})
				if i == len(matches)-1 and match['end'] < len(message)-1:
					matches_final.append({
						'key': 'DEFAULT',
						'start': match['end'],
						'end': len(message),
						'text': message[match['end']:]
					})

			if len(matches) == 0:
				matches_final.append({
					'key': 'DEFAULT',
					'start': 0,
					'end': len(message),
					'text': message
				})

			for match in matches_final:
				msg['sub_message'] = match['text']
				msg_obj = self.actions[match['key']].action(msg)

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
			logger.warn(f'Unable to handle inbound WS message: {e}')
			logger.warn(f'Message: {msg}')

				
	def on_error(self, ws, msg):
		self.connected = False
		logger.warn(f'An error has occurred: {msg}')
		return

	def on_close(self, ws, close_status_code, msg):
		self.connected = False
		logger.info(f'Closed: {close_status_code} \n - {msg}')
		return

	#Authentication
	async def update_stored_creds(self, token, refresh):
		logger.info("Access token refreshed successfully")
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
			logger.info("Cannot run authorization")

	async def reauth(self):
		if bool(self.refresh_token):
			logger.info("Attempting to refresh access token")

			if self.reauth_last - time.time() < self.reauth_window:
				logger.info(f"Reauth too soon: Must be after {self.reauth_window} s")
				self.reauth_window = min(self.reauth_window * 2, 16)
			else:
				self.token, self.refresh_token = await refresh_access_token(self.refresh_token, self.config['GENERAL']['twitchappid'], self.config['GENERAL']['twitchappsecret'])

				self.reauth_window = 1
				self.reauth_last = time.time()
				await self.update_stored_creds(self.token, self.refresh_token)
		else:
			logger.info("First auth not completed, trying now")
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
			logger.info('Creating twitch websocket')
			websocket.setdefaulttimeout(10)
			self.ws_app = websocket.WebSocketApp(
				ttsController.WS_ENDPOINT,
				on_open=self.on_open,
				on_message=self.on_message,
				on_error=self.on_error,
				on_close=self.on_close
			)
		self.connected = True