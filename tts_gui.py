import asyncio
import json
import os
import PySimpleGUI as sg
import queue
import shutil
import threading
import time
from tts_controller import ttsController
from bindglobal import BindGlobal

DEVMODE = False

class ttsGui():
	def __init__(self, app: ttsController):
		# TTS Controller
		self.app = app
		self.current_queue_list = []
		self.status = 'assets/red.png'
		self.themes = sg.theme_list()
		self.socket = None

		# Hotkey listener
		bg = BindGlobal()
		bg.start()
		bg.gbind('<End>', self.skip_message)

		# Theming
		# sg.theme('DefaultNoMoreNagging')
		sg.theme('LightGrey2')

		# PSGUI
		connection = [
			sg.Text('Status:'),
			sg.Image(self.status, size=(20, 20), key='STATUS'),
			sg.Push(),
			sg.Text('Twitch Username:'),
			sg.Input(key='USERNAME', default_text=self.app.config['GENERAL']['targetchannel']),
			sg.Button('Connect', key='CONNECT')
		]

		# Messages or Modules as tabs
		queue_control = [
			[
				sg.Text('Queued Messages:'),
				sg.Push(),
				sg.Button('AI', key="MUTE_AI", button_color='white on firebrick' if not self.app.config['AI']['active'] else ('#420000', '#d4d7dd')),
				sg.Button('LUTE', key="MUTE_LUTE", button_color='white on firebrick' if not self.app.config['LUTE']['active'] else ('#420000', '#d4d7dd')),
				sg.Button('SOUND', key="MUTE_SOUND", button_color='white on firebrick' if not self.app.config['SOUND']['active'] else ('#420000', '#d4d7dd')),
				sg.Button('TTS', key="MUTE_TTS", button_color='white on firebrick' if not self.app.config['TTS']['active'] else ('#420000', '#d4d7dd')),
				sg.Button('Skip', key='SKIP', button_color='white on firebrick' if self.app.config['FLAGS']['skip'] else ('#420000', '#d4d7dd')),
				sg.Button('Pause', key='PAUSE', button_color='white on firebrick' if self.app.config['FLAGS']['pause'] else ('#420000', '#d4d7dd')),
				sg.Button('Clear', key='CLEAR', button_color='white on firebrick' if self.app.config['FLAGS']['clear'] else ('#420000', '#d4d7dd'))
			],
			[sg.Multiline(
				'',
				size=(80, 16),
				expand_x=True,
				expand_y=True,
				disabled=True,
				enable_events=True,
				key='QUEUE',
				do_not_clear=False
			)]
		]

		model_control = [
			[
				sg.Text('Voice Pairings'),
				sg.Push(),
				sg.Button('Load Sample', key='LOADSAMPLE'),
				sg.Button('Add', key='ADDVOICE'),
				sg.Button('Remove', key='REMOVEVOICE')
			],
			[
				sg.Input('Keyword', size=(15, 1), key='SAMPLEKEY'),
				sg.Combo([s for s in os.listdir(self.app.config['AI']['samplesdir'])], expand_x=True, readonly=True, key='SAMPLE_LIST')
			],
			[
				sg.Listbox(
					[
						f"{key}: {self.app.config['AI']['speakers'][key]}" for key in self.app.config['AI']['speakers'].keys()
					],
					size=(20, 16), expand_x=True, expand_y=True, enable_events=True, key='SAMPLES_KEYS'
				)
			]
		]

		sound_control = [
			[
				sg.Text('Sound Pairings'),
				sg.Push(),
				sg.Button('Load Sound', key='LOADSOUND'),
				sg.Button('Add', key='ADDSOUND'),
				sg.Button('Remove', key='REMOVESOUND')
			],
			[
				sg.Input('Keyword', size=(15, 1), key='SOUNDKEY'),
				sg.Combo([s for s in os.listdir(self.app.config['SOUND']['soundsdir'])], expand_x=True, readonly=True, key='SOUND_LIST')
			],
			[
				sg.Listbox(
					[
						 f"{key}: {self.app.config['SOUND']['sounds'][key]}" for key in self.app.config['SOUND']['sounds'].keys()
					],
					size=(20, 16), expand_x=True, expand_y=True, enable_events=True, key='SOUNDS_KEYS'
				)
			]
		]

		config_control = [
			[
				sg.TabGroup([[
					sg.Tab('General', [
						[
							sg.Text('Username:'),
							sg.Text(self.app.config['GENERAL']['targetchannel'])
						],
						[
							sg.Text('Output Directory:'),
							sg.Input(default_text=self.app.config['GENERAL']['outputdir'], key='OUTPUTDIR')
						],
						[
							sg.Text('AI Sample Directory:'),
							sg.Input(default_text=self.app.config['GENERAL']['modeldir'], key='MODELDIR')
						],
						[
							sg.Text('Assets Directory:'),
							sg.Input(default_text=self.app.config['GENERAL']['assetsdir'], key='ASSETSDIR')
						],
						[
							sg.Text('Twitch App ID:'),
							sg.Input(default_text=self.app.config['GENERAL']['twitchappid'], key='APPID')
						],
						[
							sg.Text('Twitch Secret ID:'),
							sg.Input(default_text=self.app.config['GENERAL']['twitchappsecret'], password_char='*', key='APPSECRET')
						],
						[
							sg.Text('Action Trigger Value:'),
							sg.Input(default_text=self.app.config['GENERAL']['split_text'], key='SPLIT_TEXT')
						]
					]),
					sg.Tab('AI', [
						[
							sg.Checkbox(text='Active', key='AI_ACTIVE', default=self.app.config['AI']['active'])
						],
						[ sg.HorizontalSeparator() ],
						[ sg.Text('Cost (must be more than 0 to activate):') ],
						[
							sg.Text('Bits:'),
							sg.Push(),
							sg.Input(key='AI_BITS', default_text=self.app.config['AI']['costs']['bits'])
						],
						[
							sg.Text('Donations (WIP):'),
							sg.Push(),
							sg.Input(key='AI_DONO', default_text=self.app.config['AI']['costs']['donations'])
						],
						[
							sg.Text('Subscriptions:'),
							sg.Push(),
							sg.Input(key='AI_SUBS', default_text=self.app.config['AI']['costs']['subscriptions'])
						]
					]),
					sg.Tab('Lute', [
						[
							sg.Checkbox(text='Active', key='LUTE_ACTIVE', default=self.app.config['LUTE']['active'])
						],
						[
							sg.Checkbox(text='Pause Music (attempts to pause background music on Windows)', key='LUTE_PAUSEMUSIC', default=self.app.config['LUTE']['pause_music'])
						],
						[ sg.HorizontalSeparator() ],
						[ sg.Text('Cost (must be more than 0 to activate):') ],
						[
							sg.Text('Bits:'),
							sg.Push(),
							sg.Input(key='LUTE_BITS', default_text=self.app.config['LUTE']['costs']['bits'])
						],
						[
							sg.Text('Donations (WIP):'),
							sg.Push(),
							sg.Input(key='LUTE_DONO', default_text=self.app.config['LUTE']['costs']['donations'])
						],
						[
							sg.Text('Subscriptions:'),
							sg.Push(),
							sg.Input(key='LUTE_SUBS', default_text=self.app.config['LUTE']['costs']['subscriptions'])
						]
					]),
					sg.Tab('Sound', [
						[
							sg.Checkbox(text='Active', key='SOUND_ACTIVE', default=self.app.config['SOUND']['active'])
						],
						[ sg.HorizontalSeparator() ],
						[ sg.Text('Cost (must be more than 0 to activate):') ],
						[
							sg.Text('Bits:'),
							sg.Push(),
							sg.Input(key='SOUND_BITS', default_text=self.app.config['SOUND']['costs']['bits'])
						],
						[
							sg.Text('Donations (WIP):'),
							sg.Push(),
							sg.Input(key='SOUND_DONO', default_text=self.app.config['SOUND']['costs']['donations'])
						],
						[
							sg.Text('Subscriptions:'),
							sg.Push(),
							sg.Input(key='SOUND_SUBS', default_text=self.app.config['SOUND']['costs']['subscriptions'])
						]
					]),
					sg.Tab('TTS', [
						[
							sg.Checkbox(text='Active', key='TTS_ACTIVE', default=self.app.config['TTS']['active'])
						],
						[
							sg.Text('StreamElements Key:'),
							sg.Input(default_text=self.app.config['TTS']['streamelementskey'], password_char='*', key='STREAMELEMENTSKEY')
						],
						[ sg.HorizontalSeparator() ],
						[ sg.Text('Cost (must be more than 0 to activate):') ],
						[
							sg.Text('Bits:'),
							sg.Push(),
							sg.Input(key='TTS_BITS', default_text=self.app.config['TTS']['costs']['bits'])
						],
						[
							sg.Text('Donations (WIP):'),
							sg.Push(),
							sg.Input(key='TTS_DONO', default_text=self.app.config['TTS']['costs']['donations'])
						],
						[
							sg.Text('Subscriptions:'),
							sg.Push(),
							sg.Input(key='TTS_SUBS', default_text=self.app.config['TTS']['costs']['subscriptions'])
						]
					]),
				]], expand_x=True, expand_y=True)
			],
			[
				sg.Push(),
				sg.Button('Save', key='SAVECONFIG')
			]
		]

		tabs = sg.TabGroup([[
			sg.Tab('Queue', queue_control),
			sg.Tab('Speakers', model_control),
			sg.Tab('Sounds', sound_control),
			sg.Tab('Config', config_control)
		]], expand_x=True)

		message = [
			sg.Push(),
			sg.Text('New Message:'),
			sg.Input(key='MSG'),
			sg.Button('Add Msg', key='ADDMSG')
		]

		layout = [
			[connection],
			[tabs],
			[message]
		]

		self.window = sg.Window('Custom TTS', layout, icon='assets/sir.ico', finalize=True, size=(620, 540))
		self.window['USERNAME'].bind('<Return>', '_Enter')
		self.window['MSG'].bind('<Return>', '_Enter')

		multiline = self.window['QUEUE'].widget
		# multiline.tag_configure('fakesel', background='light grey', underline=1)
		multiline.tag_configure('indent', lmargin2=50)

		bindtags = list(multiline.bindtags())
		bindtags.remove('Text')
		multiline.bindtags(tuple(bindtags))

		self.window['QUEUE'].bind('<Button-1>', ' Click')

		def yscroll(event, widget):
			if event.num == 5 or event.delta < 0:
				widget.yview_scroll(1, 'unit')
			elif event.num == 4 or event.delta > 0:
				widget.yview_scroll(-1, 'unit')

		multiline.bind('<MouseWheel>', lambda event, widget=multiline: yscroll(event, widget))
		multiline.configure(spacing1=0, spacing2=0, spacing3=8)

		# Run the window capturing events
		while True:
			event, values = self.window.read(timeout=500)

			# Standard operations
			if event in (None, sg.WINDOW_CLOSED, 'Quit', 'Exit'):
				# Clean the outputs, if they got saved or crash
				bg.stop()
				self.clear_queue()
				self.app.shutdown()
				break

			# App operations
			if event in ('CONNECT', 'USERNAME_Enter'):
				if values['USERNAME'] != '':
					if self.app.config['GENERAL']['twitchappid'] == '' or self.app.config['GENERAL']['twitchappsecret'] == '':
						sg.popup('You must enter a Twitch App ID and Twitch App Secret in the config tab.', title='Missing Data')
					else:
						try:
							# Start workers and websocket
							self.app.config['GENERAL']['targetchannel'] = values['USERNAME']
							self.app.save_config()
							asyncio.run(self.app.auth())
						except Exception as ex:
							sg.popup(f'Failed to connect to user. Please try again: {ex}', title='Connection Failed')
				else:
					sg.popup('You must enter a Twitch Username', title='Missing Data')
			elif event in ('MUTE_LUTE', 'MUTE_TTS', 'MUTE_AI', 'MUTE_SOUND'):
				action_type = event.split('_')[1]
				action_active = self.app.config[action_type]['active']

				self.app.config[action_type]['active'] = not action_active
				self.app.save_config()
				self.window[event].update(button_color='white on firebrick' if action_active else ('#420000', '#d4d7dd'))
			elif event == 'SKIP':
				self.app.config['FLAGS']['skip'] = True
			elif event == 'PAUSE':
				self.app.config['FLAGS']['pause'] = not self.app.config['FLAGS']['pause']
				if self.app.config['FLAGS']['pause']:
					self.pause_queue()
				else:
					self.resume_queue()
			elif event == 'CLEAR':
				self.clear_queue()
			elif event in ('ADDMSG', 'MSG_Enter'):
				if values['MSG'] != '':
					# TODO - Data needs to go through the on_message(ws, msg) input
					data = json.dumps({
						'metadata': {
							'message_type': 'notification'
						},
						'payload': {
							'subscription': {
								'type': 'channel.cheer',
								'cost': 9999
							},
							'event': {
								'user_name': values['USERNAME'],
								'message': values['MSG']
							}
						}
					}, indent=4)
					self.app.on_message(self.app.ws_app, data)
					self.window['MSG'].update('')

			# big config save and update
			elif event == 'SAVECONFIG':
				self.app.config['GENERAL']['outputdir'] = values['OUTPUTDIR']
				self.app.config['GENERAL']['modeldir'] = values['MODELDIR']
				self.app.config['GENERAL']['assetsdir'] = values['ASSETSDIR']
				self.app.config['GENERAL']['twitchappid'] = values['APPID']
				self.app.config['GENERAL']['twitchappsecret'] = values['APPSECRET']
				self.app.config['GENERAL']['split_text'] = values['SPLIT_TEXT']

				self.app.config['AI']['active'] = values['AI_ACTIVE']
				if self.app.config['AI']['active'] and self.app.device == 'cpu':
					sg.popup('Be advised - Echo does not always work as expected when CUDA is not available. You are currently using CPU.', title='Echo CPU Warning')
				self.app.config['AI']['costs'] = {
					'bits': int(values['AI_BITS']),
					'donations': int(values['AI_DONO']),
					'subscriptions': int(values['AI_SUBS']),
				}

				self.app.config['LUTE']['active'] = values['LUTE_ACTIVE']
				self.app.config['LUTE']['costs'] = {
					'bits': int(values['LUTE_BITS']),
					'donations': int(values['LUTE_DONO']),
					'subscriptions': int(values['LUTE_SUBS']),
				}
				self.app.config['LUTE']['pause_music'] = str(values['LUTE_PAUSEMUSIC'])

				self.app.config['SOUND']['active'] = values['SOUND_ACTIVE']
				self.app.config['SOUND']['costs'] = {
					'bits': int(values['SOUND_BITS']),
					'donations': int(values['SOUND_DONO']),
					'subscriptions': int(values['SOUND_SUBS']),
				}

				self.app.config['TTS']['active'] = values['TTS_ACTIVE']
				self.app.config['TTS']['costs'] = {
					'bits': int(values['TTS_BITS']),
					'donations': int(values['TTS_DONO']),
					'subscriptions': int(values['TTS_SUBS']),
				}
				self.app.config['TTS']['streamelementskey'] = values['STREAMELEMENTSKEY']

				self.app.save_config()

			# samples
			elif event == 'LOADSAMPLE':
				file = sg.popup_get_file('Select the voice sample .wav sound you would like to add. Ideally 15-30 seconds:', title='Voice Cloning Device 42069', file_types=(('Acceptable Files', '*.wav'), ('Other Filthy File Types', '*.*')))
				if file:
					shutil.copy(file, self.app.config['AI']['samplesdir'] + file.split('/')[-1])
					self.window['SAMPLE_LIST'].update(values=[s for s in os.listdir(self.app.config['AI']['samplesdir'])]);

			elif event == 'ADDVOICE':
				if values['SAMPLEKEY'] != '' and self.window['SAMPLE_LIST'].get() != '':
					if values['SAMPLEKEY'].lower() in self.app.config['SOUND']['sounds'].keys() or \
						values['SAMPLEKEY'].lower() in self.app.config['AI']['speakers'].keys():
						sg.popup(f'The key "{values["SAMPLEKEY"]}" is already in use, please change.', title='Keyword Error')
					else:
						self.app.config['AI']['speakers'][values['SAMPLEKEY'].lower()] = self.window['SAMPLE_LIST'].get()
						self.window['SAMPLES_KEYS'].update([f'{key}: {self.app.config["AI"]["speakers"][key]}' for key in self.app.config['AI']['speakers'].keys()])
						self.window['SAMPLEKEY'].update('')
						self.app.save_config()
				else:
					sg.popup('You\'re missing either a keyword or sound selection.', title='Sound Error')

			elif event == 'REMOVEVOICE':
				samples = self.window['SAMPLES_KEYS'].get()
				for sample in samples:
					self.app.config['AI']['speakers'] = self.app.config['AI']['speakers'].pop(sample.split(':')[0])
					self.window['SAMPLES_KEYS'].update([f'{key}: {self.app.config["AI"]["speakers"][key]}' for key in self.app.config['AI']['speakers'].keys()])
				self.app.save_config()

			# sound effects
			elif event == 'LOADSOUND' or event == 'FILE':
				file = sg.popup_get_file('Select the Wav or MP3 sound you would like to add:', title='Soundbath Selector 9000', file_types=(('Acceptable Files', '*.wav *.mp3'), ('Other Filthy File Types', '*.*')))
				if file:
					shutil.copy(file, self.app.config['SOUND']['soundsdir'] + file.split('/')[-1])
					self.window['SOUND_LIST'].update(values=[s for s in os.listdir(self.app.config['SOUND']['soundsdir'])]);

			elif event == 'ADDSOUND':
				if values['SOUNDKEY'] != '' and self.window['SOUND_LIST'].get() != '':
					if values['SOUNDKEY'].lower() in self.app.config['SOUND']['sounds'].keys() or \
						values['SOUNDKEY'].lower() in self.app.config['AI']['speakers'].keys():
						sg.popup(f'The key "{values["SOUNDKEY"]}" is already in use, please change.', title='Keyword Error')
					else:
						self.app.config['SOUND']['sounds'][values['SOUNDKEY'].lower()] = self.window['SOUND_LIST'].get()
						self.window['SOUNDS_KEYS'].update([f'{key}: {self.app.config["SOUND"]["sounds"][key]}' for key in self.app.config['SOUND']['sounds'].keys()])
						self.window['SOUNDKEY'].update('')
						self.app.save_config()
				else:
					sg.popup('You\'re missing either a keyword or sound selection.', title='Sound Error')

			elif event == 'REMOVESOUND':
				sounds = self.window['SOUNDS_KEYS'].get()
				for sound in sounds:
					self.app.config['SOUND']['sounds'] = self.app.config['SOUND']['sounds'].pop(sound.split(':')[0])
				self.window['SOUNDS_KEYS'].update([f'{key}: {self.app.config["SOUND"]["sounds"][key]}' for key in self.app.config['SOUND']['sounds'].keys()])
				self.app.save_config()

			# timeout issues
			elif event == sg.TIMEOUT_EVENT:
				try:
					if self.app.ws_app:
						self.status = './assets/green.png' if self.app.connected else './assets/red.png'
						self.window['STATUS'].update(self.status)
						self.window['USERNAME'].update(disabled=True)

						self.window['MUTE_AI'].update(button_color='white on firebrick' if not self.app.config['AI']['active'] else ('#420000', '#d4d7dd'))
						self.window['MUTE_LUTE'].update(button_color='white on firebrick' if not self.app.config['LUTE']['active'] else ('#420000', '#d4d7dd'))
						self.window['MUTE_SOUND'].update(button_color='white on firebrick' if not self.app.config['SOUND']['active'] else ('#420000', '#d4d7dd'))
						self.window['MUTE_TTS'].update(button_color='white on firebrick' if not self.app.config['TTS']['active'] else ('#420000', '#d4d7dd'))
						self.window['SKIP'].update(button_color='white on firebrick' if self.app.config['FLAGS']['skip'] else ('#420000', '#d4d7dd'))
						self.window['PAUSE'].update(button_color='white on firebrick' if self.app.config['FLAGS']['pause'] else ('#420000', '#d4d7dd'))
						self.window['CLEAR'].update(button_color='white on firebrick' if self.app.config['FLAGS']['clear'] else ('#420000', '#d4d7dd'))

						# Collect messages
						items = []
						messages = []
						rem_ind = -1
						for i, item in enumerate(self.app.text_list):
							if bytes(item['filename'], 'utf-8') in self.app.played_file.value:
								rem_ind = i

						for i, item in enumerate(self.app.text_list):
							if i > rem_ind:
								messages.append(item['user_name'] + ': ' + item['message'])
								items.append(item)

						if rem_ind > -1:
							self.app.text_list.pop(0)

						if messages != self.current_queue_list:
							self.current_queue_list = messages
							self.window['QUEUE'].update('\n'.join(messages))
							for tag in multiline.tag_names():
								if tag != 'fakesel' and tag != 'indent':
									multiline.tag_remove(tag, '1.0', 'end')
							for i, item in enumerate(items):
								multiline.tag_config(item['user_name'], font=('Helvetica', 10, 'bold'))
								multiline.tag_add(item['user_name'], f'{i + 1}.0', f'{i + 1}.{len(items[i]["user_name"])}')

							multiline.tag_add('indent', '1.0', 'end')

						# Constant config update
						self.app.config_manager.update(self.app.config)

						# Disconnected? Try to connect
						if not self.app.connected:
							if time.time() - self.app.reauth_last < self.app.reauth_window:
								print(f'{time.time() - self.app.reauth_last:.2f} s to soon to reconnect ({self.app.reauth_window})')
							else:
								self.app.ws_app = None
								asyncio.run(self.app.reauth())
					else:
						# Start workers and websocket
						if os.path.exists(os.path.join(self.app.config['GENERAL']['outputdir'], "credentials.json")):
							print('Credentials exist, starting WebSocket app.')
							self.window['CONNECT'].update(disabled=True)
							self.window['USERNAME'].update(disabled=True)
							asyncio.run(self.app.run())
							self.socket = threading.Thread(target=self.app.ws_app.run_forever, daemon=True)
							if self.socket and not self.socket.is_alive():
								self.socket.start()
						elif self.app.config['GENERAL']['targetchannel'] not in (None, ''):
							asyncio.run(self.app.auth())

				except Exception as e:
					print(f'Error updating the connection status and queue: ' + str(e))
					if str(e) == 'Invalid refresh token' and os.path.exists(os.path.join(self.app.config['GENERAL']['outputdir'], "credentials.json")):
						os.remove(os.path.join(self.app.config['GENERAL']['outputdir'], "credentials.json"))
						print('Reauthenticating now.')
					print('Trying update again in 2 seconds...')

		self.window.close()

	def clear_queue(self):
		print(self.app.config)
		was_paused = self.app.config['FLAGS']['pause']
		self.app.config['FLAGS']['pause'] = True 
		self.app.config['FLAGS']['clear'] = True 

		while not self.app.gen_queue.empty():
			try:
				self.app.gen_queue.get(block=False)
			except queue.Empty:
				break

		while not self.app.tts_queue.empty():
			try:
				self.app.tts_queue.get(block=False)
			except queue.Empty:
				break

		for file in os.listdir(self.app.config['GENERAL']['outputdir']):
			if file.endswith('.wav') or file.endswith('.mp3'):
				try:
					os.remove(os.path.join(self.app.config['GENERAL']['outputdir'], file))
				except:
					continue

		self.app.current_speaker = "none" if not was_paused else "paused"
		self.app.text_list = []
		self.app.config['FLAGS']['pause'] = was_paused 
		self.app.config['FLAGS']['clear'] = False 
		self.app.config['FLAGS']['skip'] = False

	def skip_message(self, e):
		self.app.config['FLAGS']['skip'] = True 

	def pause_queue(self):
		self.app.config['FLAGS']['pause'] = True 
		self.window['PAUSE'].update(text='Play', button_color='white on firebrick')

	def resume_queue(self):
		self.app.config['FLAGS']['pause'] = False 
		self.app.current_speaker = "none"
		self.window['PAUSE'].update(text='Pause', button_color=('#420000', '#d4d7dd'))
