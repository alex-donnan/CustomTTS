import asyncio
import random
from tkinter import font
from tkinter.font import Font

import json
import os
import PySimpleGUI as sg
import queue
import shutil
import time
import threading
import ttsController as TTS

DEVMODE = False

class ttsGui():
    def __init__(self, app: TTS):
        # TTS Controller
        self.app = app
        self.current_queue_list = []
        self.status = 'assets/red.png'
        self.themes = sg.theme_list()
        self.socket = None

        # Theming
        sg.theme('DefaultNoMoreNagging')

        # PSGUI
        connection = [
            sg.Text('Status:'),
            sg.Image(self.status, size=(16, 16), key='STATUS'),
            sg.Push(),
            sg.Text('Twitch Username:'),
            sg.Input(key='USERNAME', default_text=self.app.target_channel),
            sg.Button('Connect')
        ]

        # Messages or Modules as tabs
        queue_control = [
            [
                sg.Text('Queued Messages:'),
                sg.Push(),
                sg.Button('Pause', key='PAUSE'),
                sg.Button('Clear', key='CLEAR')
            ],
            [sg.Multiline('', size=(80, 16), expand_x=True, disabled=True, enable_events=True, key='QUEUE',
                          do_not_clear=False)]
        ]

        speaker_list = []
        for key in self.app.tts_synth.keys():
            if self.app.tts_synth[key].tts_model.speaker_manager is not None:
                for speaker in self.app.tts_synth[key].tts_model.speaker_manager.speaker_names:
                    speaker_list.append(key + ': ' + speaker)
            else:
                speaker_list.append(key)

        model_control = [
            [
                sg.Text('Voice Pairings'),
                sg.Push(),
                sg.Button('Add', key='ADDVOICE'),
                sg.Button('Remove', key='REMOVEVOICE')
            ],
            [
                sg.Input('Keyword', size=(15, 1), key='KEY'),
                sg.Combo(speaker_list, expand_x=True, readonly=True, key='VOICE')
            ],
            [sg.Listbox([key + ': ' +
                         self.app.speaker_list[key]['model'] +
                         (' - ' + self.app.speaker_list[key]['speaker']
                        if self.app.speaker_list[key]['speaker'] is not None else '')
                         for key in self.app.speaker_list.keys()],
                        size=(20, 16), expand_x=True, enable_events=True, key='VOICES')]
        ]

        sound_list = []
        for file in os.listdir(self.app.asset_path):
            if file.endswith('wav'):
                sound_list.append(file)

        sound_control = [
            [
                sg.Text('Sound Pairings'),
                sg.Push(),
                sg.Button('Load Wav', key='LOADSOUND'),
                sg.Button('Add', key='ADDSOUND'),
                sg.Button('Remove', key='REMOVESOUND')
            ],
            [
                sg.Input('Keyword', size=(15, 1), key='SOUNDKEY'),
                sg.Combo(sound_list, expand_x=True, readonly=True, key='SOUND')
            ],
            [sg.Listbox([f'{key}: {self.app.sound_list[key]}' for key in self.app.sound_list.keys()],
                        size=(20, 16), expand_x=True, enable_events=True, key='SOUNDS')]
        ]

        tabs = sg.TabGroup([[
            sg.Tab('Queue', queue_control),
            sg.Tab('Speakers', model_control),
            sg.Tab('Sounds', sound_control)
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

        self.window = sg.Window('Custom TTS', layout, icon='assets/sir.ico', finalize=True)
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

        self.refresh_thread = threading.Thread(target=self.refresh_queue, args={multiline}, daemon=True)
        self.refresh_thread.start()

        # Run the window capturing events
        while True:
            event, values = self.window.read()
            print(event)

            # Standard operations
            if event in (None, sg.WINDOW_CLOSED, 'Quit', 'Exit'):
                # Clean the outputs, if they got saved or crash
                self.clear_queue()
                print('Closing app.')
                break

            # App operations
            elif event in ('Connect', 'USERNAME_Enter'):
                if values['USERNAME'] != '':
                    try:
                        #Start workers and websocket
                        self.app.set_channel(values['USERNAME'])
                        asyncio.run(self.app.auth())
                    except Exception as ex:
                        sg.popup(f'Failed to connect to user. Please try again: {ex}', title='Connection Failed')
                else:
                    sg.popup(f'You must enter a Twitch Username', title='Missing Data')
            elif event == 'PAUSE':
                self.app.pause_flag = not self.app.pause_flag
                self.window['PAUSE'].update('Play' if self.app.pause_flag else 'Pause')
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
                                'cost': 1
                            },
                            'event': {
                                'user_name': values['USERNAME'],
                                'message': values['MSG']
                            }
                        }
                    }, indent=4)
                    self.app.on_message(self.app.wsapp, data)
                    self.window['MSG'].update('')
            elif event == 'ADDVOICE':
                if values['KEY'] != '':
                    self.window['KEY'].update('')
                    voice_object = {
                        'model': values['VOICE'].split(': ')[0],
                        'speaker': values['VOICE'].split(': ')[1] if len(values['VOICE'].split(': ')) > 1 else None
                    }
                    self.app.speaker_list[values['KEY']] = voice_object

                    self.window['VOICES'].update([key + ': ' +
                                                  self.app.speaker_list[key]['model'] +
                                                  (' - ' + self.app.speaker_list[key]['speaker']
                                                   if self.app.speaker_list[key]['speaker'] is not None else '')
                                                  for key in self.app.speaker_list.keys()])
                    self.app.config.set('DEFAULT', 'Speakers', str(self.app.speaker_list))
                    with open('config.ini', 'w') as configfile:
                        self.app.config.write(configfile)
                else:
                    sg.popup(f'You\'re missing either a keyword or voice selection.')
            elif event == 'REMOVEVOICE':
                voices = self.window['VOICES'].get()
                for voice in voices:
                    self.app.speaker_list.pop(voice.split(':')[0])
                self.window['VOICES'].update([key + ': ' +
                                              self.app.speaker_list[key]['model'] +
                                              (' - ' + self.app.speaker_list[key]['speaker']
                                               if self.app.speaker_list[key]['speaker'] is not None else '')
                                              for key in self.app.speaker_list.keys()])
                self.app.config.set('DEFAULT', 'Speakers', str(self.app.speaker_list))
                with open('config.ini', 'w') as configfile:
                    self.app.config.write(configfile)
            elif event == 'LOADSOUND' or event == 'FILE':
                file = sg.popup_get_file('Select the WAV you would like to add:', title='WAV Selector 9000', file_types=(('WAV Files', '*.wav'), ('ALL Files', '*.*')))
                if file:
                    shutil.copy(file, self.app.asset_path + file.split('/')[-1])

                    sound_list = []
                    for file in os.listdir(self.app.asset_path):
                        if file.endswith('wav'):
                            sound_list.append(file)
                    self.window['SOUND'].update(values=sound_list);
            elif event == 'ADDSOUND':
                if values['SOUNDKEY'] != '':
                    self.window['SOUNDKEY'].update('')
                    self.app.sound_list[values['SOUNDKEY']] = values['SOUND'].lower()
                    self.window['SOUNDS'].update([f'{key}: {self.app.sound_list[key]}' for key in self.app.sound_list.keys()])
                    self.app.config.set('DEFAULT', 'Sounds', str(self.app.sound_list))
                    with open('config.ini', 'w') as configfile:
                        self.app.config.write(configfile)
                else:
                    sg.popup('You\'re missing either a keyword or sound selection.')
            elif event == 'REMOVESOUND':
                sounds = self.window['SOUNDS'].get()
                for sound in sounds:
                    self.app.sound_list.pop(sound.split(':')[0])
                self.window['SOUNDS'].update([f'{key}: {self.app.sound_list[key]}' for key in self.app.sound_list.keys()])
                self.app.config.set('DEFAULT', 'Sounds', str(self.app.sound_list))
                with open('config.ini', 'w') as configfile:
                    self.app.config.write(configfile)

        self.window.close()

    def refresh_queue(self, multiline=None):
        while True:
            # Update connection status
            try:
                if self.app.wsapp:
                    self.status = 'assets/green.png' if self.app.connected else 'assets/red.png'
                    self.window['STATUS'].update(self.status)

                    # Collect messages
                    items = []
                    messages = []
                    for item in self.app.tts_text:
                        messages.append(item['user_name'] + ': ' + item['chat_message'])
                        items.append(item)

                    if messages != self.current_queue_list:
                        self.current_queue_list = messages
                        self.window['QUEUE'].update('\n'.join(messages))
                        for tag in multiline.tag_names():
                            if tag != 'fakesel' and tag != 'indent':
                                multiline.tag_remove(tag, '1.0', 'end')
                        for i in range(len(items)):
                            multiline.tag_config(item['user_name'], font=('Helvetica', 10, 'bold'))
                            multiline.tag_add(item['user_name'], f'{i+1}.0',
                                              f'{i+1}.{len(items[i]["user_name"])}')

                        multiline.tag_add('indent', '1.0', 'end')

                    time.sleep(1)

                    # Disconnected? Try to connect
                    if not self.app.connected:
                        self.socket.start()
                else:
                    if os.path.exists(self.app.credentials_path):
                        print('Credentials exist, starting WebSocket app.')
                        asyncio.run(self.app.run())
                        self.socket = threading.Thread(target=self.app.wsapp.run_forever, daemon=True)
                        self.socket.start()

                        #safety
                        time.sleep(2)
            except Exception as e:
                print(f'Error updating the connection status and queue: ' + str(e))
                print('Trying update again in 2 seconds...')
                time.sleep(2)

    def clear_queue(self):
        was_paused = self.app.pause_flag
        self.app.pause_flag = True
        self.app.clear_flag = True
            
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

        for file in os.listdir(self.app.output_path):
            if file.endswith('.wav') or file.endswith('.mp3'):
                try: os.remove(os.path.join(self.app.output_path, file))
                except: continue

        self.app.tts_text = []
        self.app.pause_flag = was_paused

if __name__ == '__main__':
    controller = TTS.ttsController()
    window = ttsGui(app=controller)