import asyncio
import json
import os
import PySimpleGUI as sg
import queue
import shutil
import threading
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
        self.load_thread = None

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
            sg.Input(key='USERNAME', default_text=self.app.config['DEFAULT']['targetchannel']),
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
                sg.Button('Skip', key='SKIP'),
                sg.Button('Pause', key='PAUSE'),
                sg.Button('Clear', key='CLEAR')
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
                        f"{key}: {self.app.speaker_list[key]}" for key in self.app.speaker_list.keys()
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
                         f"{key}: {self.app.sound_list[key]}" for key in self.app.sound_list.keys()
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
                            sg.Text(self.app.config['DEFAULT']['targetchannel'])
                        ],
                        [
                            sg.Text('Output Directory:'),
                            sg.Input(default_text=self.app.config['DEFAULT']['outputdir'], key='OUTPUTDIR')
                        ],
                        [
                            sg.Text('AI Sample Directory:'),
                            sg.Input(default_text=self.app.config['DEFAULT']['modeldir'], key='MODELDIR')
                        ],
                        [
                            sg.Text('Assets Directory:'),
                            sg.Input(default_text=self.app.config['DEFAULT']['assetsdir'], key='ASSETSDIR')
                        ],
                        [
                            sg.Text('Twitch App ID:'),
                            sg.Input(default_text=self.app.config['DEFAULT']['twitchappid'], key='APPID')
                        ],
                        [
                            sg.Text('Twitch Secret ID:'),
                            sg.Input(default_text=self.app.config['DEFAULT']['twitchappsecret'], password_char='*', key='APPSECRET')
                        ]
                    ]),
                    sg.Tab('AI', [
                        [
                            sg.Checkbox(text='Active:', key='AI_ACTIVE')
                        ],
                        [
                            sg.Text('Cost (must be more than 0 to activate):')
                        ]
                    ]),
                    sg.Tab('Lute', [

                    ]),
                    sg.Tab('TTS', [

                    ]),
                    sg.Tab('Sound', [

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
                self.clear_queue()
                bg.stop()
                self.app.echo.unload_models()
                print('Closing app.')
                break

            # Twitch chat commands
            if not self.app.config['FLAGS'].getboolean('pause'):
                self.pause_queue()
            if self.app.config['FLAGS'].getboolean('pause'):
                self.resume_queue()
            if self.app.config['FLAGS'].getboolean('clear'):
                self.clear_queue()

            # App operations
            if event in ('CONNECT', 'USERNAME_Enter'):
                if values['USERNAME'] != '':
                    try:
                        # Start workers and websocket
                        self.app.config.set('DEFAULT', 'TargetChannel', values['USERNAME'])
                        self.app.save_config()
                        asyncio.run(self.app.auth())
                    except Exception as ex:
                        sg.popup(f'Failed to connect to user. Please try again: {ex}', title='Connection Failed')
                else:
                    sg.popup(f'You must enter a Twitch Username', title='Missing Data')
            elif event in ('MUTE_LUTE', 'MUTE_TTS', 'MUTE_AI', 'MUTE_SOUND'):
                action_type = event.split('_')[1]
                action_active = self.app.config[action_type].getboolean('active')

                print(f'{action_type} - {action_active}')

                self.app.config.set(action_type, 'active', str(not action_active))
                self.app.save_config()
                self.window[event].update(button_color='white on firebrick' if action_active else ('#420000', '#d4d7dd'))
            elif event == 'SKIP':
                self.app.config.set('FLAGS', 'skip', str(True))
            elif event == 'PAUSE':
                self.app.config.set('FLAGS', 'pause', str(not self.app.config['FLAGS'].getboolean('pause')))
                if self.app.config['FLAGS'].getboolean('pause'):
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
                    self.app.on_message(self.app.wsapp, data)
                    self.window['MSG'].update('')

            # samples
            elif event == 'LOADSAMPLE':
                file = sg.popup_get_file('Select the voice sample .wav sound you would like to add. Ideally 15-30 seconds:', title='Voice Cloning Device 42069', file_types=(('Acceptable Files', '*.wav'), ('Other Filthy File Types', '*.*')))
                if file:
                    shutil.copy(file, self.app.config['AI']['samplesdir'] + file.split('/')[-1])
                    self.window['SAMPLES_LIST'].update(values=[s for s in os.listdir(self.app.config['AI']['samplesdir'])]);

            elif event == 'ADDVOICE':
                if values['SAMPLEKEY'] != '' and self.window['SAMPLE_LIST'].get() != '':
                    if values['SAMPLEKEY'].lower() in self.app.sound_list.keys() or \
                        values['SAMPLEKEY'].lower() in self.app.speaker_list.keys():
                        sg.popup(f'The key "{values["SAMPLEKEY"]}" is already in use, please change.', title='Keyword Error')
                    else:
                        self.window['SAMPLEKEY'].update('')
                        self.app.speaker_list[values['SAMPLEKEY'].lower()] = self.window['SAMPLE_LIST'].get()
                        self.window['SAMPLES_KEYS'].update([f'{key}: {self.app.speaker_list[key]}' for key in self.app.speaker_list.keys()])
                        self.app.config.set('AI', 'speakers', str(self.app.speaker_list))
                        self.app.save_config()
                        self.app.echo.add_speaker(values['SAMPLEKEY'], self.window['SAMPLE_LIST'].get())
                else:
                    sg.popup('You\'re missing either a keyword or sound selection.', title='Sound Error')

            elif event == 'REMOVEVOICE':
                samples = self.window['SAMPLES_KEYS'].get()
                for sample in samples:
                    self.app.speaker_list.pop(sample.split(':')[0])
                self.window['SAMPLES_KEYS'].update([f'{key}: {self.app.speaker_list[key]}' for key in self.app.speaker_list.keys()])
                self.app.config.set('AI', 'speakers', str(self.app.speaker_list))
                self.app.save_config()

            # sound effects
            elif event == 'LOADSOUND' or event == 'FILE':
                file = sg.popup_get_file('Select the Wav or MP3 sound you would like to add:', title='Soundbath Selector 9000', file_types=(('Acceptable Files', '*.wav *.mp3'), ('Other Filthy File Types', '*.*')))
                if file:
                    shutil.copy(file, self.app.config['SOUND']['soundsdir'] + file.split('/')[-1])
                    self.window['SOUND_LIST'].update(values=[s for s in os.listdir(self.app.config['SOUND']['soundsdir'])]);

            elif event == 'ADDSOUND':
                if values['SOUNDKEY'] != '' and self.window['SOUND_LIST'].get() != '':
                    if values['SOUNDKEY'].lower() in self.app.sound_list.keys() or \
                        values['SOUNDKEY'].lower() in self.app.speaker_list.keys():
                        sg.popup(f'The key "{values["SOUNDKEY"]}" is already in use, please change.', title='Keyword Error')
                    else:
                        self.window['SOUNDKEY'].update('')
                        self.app.sound_list[values['SOUNDKEY'].lower()] = self.window['SOUND_LIST'].get()
                        self.window['SOUNDS_KEYS'].update([f'{key}: {self.app.sound_list[key]}' for key in self.app.sound_list.keys()])
                        self.app.config.set('SOUND', 'sounds', str(self.app.sound_list))
                        self.app.save_config()
                else:
                    sg.popup('You\'re missing either a keyword or sound selection.', title='Sound Error')

            elif event == 'REMOVESOUND':
                sounds = self.window['SOUNDS_KEYS'].get()
                for sound in sounds:
                    self.app.sound_list.pop(sound.split(':')[0])
                self.window['SOUNDS_KEYS'].update([f'{key}: {self.app.sound_list[key]}' for key in self.app.sound_list.keys()])
                self.app.config.set('SOUND', 'sounds', str(self.app.sound_list))
                self.app.save_config()

            # timeout issues
            elif event == sg.TIMEOUT_EVENT:
                try:
                    if self.app.wsapp:
                        self.status = './assets/green.png' if self.app.connected else './assets/red.png'
                        self.window['STATUS'].update(self.status)
                        self.window['CONNECT'].update(disabled=True)
                        self.window['USERNAME'].update(disabled=True)

                        # Collect messages
                        items = []
                        messages = []
                        for item in self.app.tts_text:
                            messages.append(item['user_name'] + ': ' + item['message'])
                            items.append(item)

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

                        if self.load_thread and not self.load_thread.is_alive():
                            speaker_list = []
                            for key in self.app.echo.speaker_samples.keys():
                                speaker_list.append(f'{key}: {self.app.echo.speaker_samples[key]}')
                            self.window['VOICE'].update(values=speaker_list)
                            self.load_thread = None

                        # Disconnected? Try to connect
                        if not self.app.connected:
                            self.app.wsapp = None
                            asyncio.run(self.app.reauth())
                    else:
                        # Start workers and websocket
                        if os.path.exists(os.path.join(self.app.config['DEFAULT']['OutputDir'], "credentials.json")):
                            print('Credentials exist, starting WebSocket app.')
                            self.window['CONNECT'].update(disabled=True)
                            self.window['USERNAME'].update(disabled=True)
                            asyncio.run(self.app.run())
                            self.socket = threading.Thread(target=self.app.wsapp.run_forever, daemon=True)
                            if self.socket and not self.socket.is_alive():
                                self.socket.start()
                        elif self.app.config['DEFAULT']['targetchannel'] not in (None, ''):
                            asyncio.run(self.app.auth())

                except Exception as e:
                    print(f'Error updating the connection status and queue: ' + str(e))
                    if str(e) == 'Invalid refresh token' and os.path.exists(os.path.join(self.app.config['DEFAULT']['OutputDir'], "credentials.json")):
                        os.remove(os.path.join(self.app.config['DEFAULT']['OutputDir'], "credentials.json"))
                        print('Reauthenticating now.')
                    print('Trying update again in 2 seconds...')

        self.window.close()

    def clear_queue(self):
        was_paused = self.app.config['FLAGS'].getboolean('pause')
        self.app.config.set('FLAGS', 'pause', str(True))
        self.app.config.set('FLAGS', 'clear', str(True))

        while not self.app.gen_queue.empty():
            try:
                self.app.gen_queue.get(block=False)
                self.app.gen_queue.task_done()
            except queue.Empty:
                break

        while not self.app.tts_queue.empty():
            try:
                self.app.tts_queue.get(block=False)
                self.app.tts_queue.task_done()
            except queue.Empty:
                break

        for file in os.listdir(self.app.config['DEFAULT']['outputdir']):
            if file.endswith('.wav') or file.endswith('.mp3'):
                try:
                    os.remove(os.path.join(self.app.config['DEFAULT']['outputdir'], file))
                except:
                    continue

        self.app.current_speaker = "none" if not was_paused else "paused"
        self.app.tts_text = []
        self.app.config.set('FLAGS', 'pause', str(was_paused))

    def skip_message(self, e):
        self.app.config.set('FLAGS', 'skip', str(True))

    def pause_queue(self):
        self.app.config.set('FLAGS', 'pause', str(True))
        self.window['PAUSE'].update(text='Play', button_color='white on firebrick')

    def resume_queue(self):
        self.app.config.set('FLAGS', 'pause', str(False))
        self.app.current_speaker = "none"
        self.window['PAUSE'].update(text='Pause', button_color=('#420000', '#d4d7dd'))

if __name__ == '__main__':
    controller = ttsController()
    window = ttsGui(app=controller)