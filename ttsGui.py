import asyncio
import random
from tkinter import font
from tkinter.font import Font

import PySimpleGUI as sg
import queue
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
                    speaker_list.append(key + ": " + speaker)
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
                sg.Input('keyword', size=(15, 1), key='KEY'),
                sg.Combo(speaker_list, expand_x=True, readonly=True, key='VOICE')
            ],
            [sg.Listbox([key + ': ' +
                         self.app.speaker_list[key]['model'] +
                         (' - ' + self.app.speaker_list[key]['speaker']
                        if self.app.speaker_list[key]['speaker'] is not None else '')
                         for key in self.app.speaker_list.keys()],
                        size=(20, 16), expand_x=True, enable_events=True, key='VOICES')]
        ]
        tabs = sg.TabGroup([[
            sg.Tab('Queue', queue_control),
            sg.Tab('Speakers', model_control)
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
        self.window['USERNAME'].bind("<Return>", "_Enter")
        self.window['MSG'].bind("<Return>", "_Enter")

        multiline = self.window['QUEUE'].widget
        # multiline.tag_configure('fakesel', background='light grey', underline=1)
        multiline.tag_configure('indent', lmargin2=50)

        bindtags = list(multiline.bindtags())
        bindtags.remove("Text")
        multiline.bindtags(tuple(bindtags))

        self.window['QUEUE'].bind('<Button-1>', ' Click')

        def yscroll(event, widget):
            if event.num == 5 or event.delta < 0:
                widget.yview_scroll(1, "unit")
            elif event.num == 4 or event.delta > 0:
                widget.yview_scroll(-1, "unit")

        multiline.bind('<MouseWheel>', lambda event, widget=multiline: yscroll(event, widget))

        multiline.configure(spacing1=0, spacing2=0, spacing3=8)

        self.refresh_thread = threading.Thread(target=self.refresh_queue, args={multiline}, daemon=True)
        self.refresh_thread.start()

        # Run the window capturing events
        while True:
            event, values = self.window.read()

            # Standard operations
            if event in (None, sg.WINDOW_CLOSED, 'Quit', 'Exit'):
                print('Closing app.')
                break

            # App operations
            elif event in ('Connect', 'USERNAME_Enter'):
                if values['USERNAME'] != '':
                    try:
                        #Start workers and websocket
                        self.app.set_channel(values['USERNAME'])
                        threading.Thread(target=self.app.worker, daemon=True).start()
                        asyncio.run(self.app.run())
                        threading.Thread(target=self.app.wsapp.run_forever, daemon=True).start()

                        #Switch to disconnect?

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
                    data = {'bits_used': 1, 'user_name': values['USERNAME'], 'chat_message': values['MSG']}
                    self.app.tts_queue.put(data)
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
            # elif event == 'QUEUE Click':
            #     e = self.window['QUEUE'].user_bind_event
            #     line, column = multiline.index(f"@{e.x},{e.y}").split(".")
            #     multiline.tag_remove('fakesel', "1.0", 'end')
            #     multiline.tag_add('fakesel', f'{line}.0', f'{line}.end')
            #     multiline.tag_remove('sel', "1.0", 'end')
            #     multiline.tag_add('sel', f'{line}.0', f'{line}.end')
            #     ranges = multiline.tag_ranges('sel')
            #     if ranges:
            #         print('SELECTED Text is %r' % multiline.get(*ranges))
            #     else:
            #         print('NO Selected Text')

        self.window.close()


    def refresh_queue(self, multiline=None):
        while True:
            # Update connection status
            try:
                self.status = 'assets/green.png' if self.app.connected else 'assets/red.png'
                self.window['STATUS'].update(self.status)               

                # Collect messages
                with self.app.tts_queue.mutex:
                    items = []
                    messages = []
                    for item in list(self.app.tts_queue.queue):
                        messages.append(item['user_name'] + ': ' + item['chat_message'])
                        items.append(item)

                    if messages != self.current_queue_list:
                        self.current_queue_list = messages
                        self.window['QUEUE'].update('\n'.join(messages))
                        for tag in multiline.tag_names():
                            if tag != "fakesel" and tag != "indent":
                                multiline.tag_remove(tag, '1.0', 'end')
                        for i in range(len(items)):
                            multiline.tag_config(item['user_name'], font=('Helvetica', 10, 'bold'))
                            multiline.tag_add(item['user_name'], f'{i+1}.0',
                                              f'{i+1}.{len(items[i]["user_name"])}')

                        multiline.tag_add('indent', '1.0', 'end')

                time.sleep(0.5)
            except Exception as e:
                print(f'Error updating the connection status and queue...' + str(e))

    def clear_queue(self):
        was_paused = self.app.pause_flag
        self.app.pause_flag = True
        self.app.clear_flag = True
        while not self.app.tts_queue.empty():
            try:
                self.app.tts_queue.get(block=False)
            except queue.Empty:
                break
            self.app.tts_queue.task_done()
        self.app.pause_flag = was_paused


if __name__ == '__main__':
    controller = TTS.ttsController()
    window = ttsGui(app=controller)