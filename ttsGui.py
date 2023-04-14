import asyncio
import distutils.dir_util
import os
import PySimpleGUI as sg
import queue
import time
import threading
import ttsController as TTS

dev_mode = True


class ttsGui():
    def __init__(self, app: TTS):
        # TTS Controller
        self.app = app
        self.current_queue_list = []
        self.listener = ()
        self.models = []
        self.model_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'tts')
        self.status = 'assets/red.png'
        self.themes = sg.theme_list()

        #Theming
        sg.theme('DefaultNoMoreNagging')
        #sg.theme('DarkBlack1')

        # PSGUI
        connection=[
            sg.Text('Status:'),
            sg.Image(self.status, size=(16, 16), key='STATUS'),
            sg.Push(),
            sg.Text('Twitch Username:'),
            sg.Input(key='USERNAME', default_text=self.app.target_channel),
            sg.Button('Connect')
        ]

        #Messages or Modules as tabs
        queue_control=[
            [
                sg.Text('Queued Messages:'),
                sg.Push(),
                sg.Button('Pause', key='PAUSE'),
                sg.Button('Clear', key='CLEAR')
            ],
            [sg.Listbox([], size=(20, 18), expand_x=True, enable_events=True, key='QUEUE')]
        ]
        model_control=[
            [
                sg.Text('Voice Pairings'),
                sg.Push(),
                sg.Button('Add', key='ADDVOICE'),
                sg.Button('Remove', key='REMOVEVOICE')
            ],
            [
                sg.Input('keyword', size=(15,1), key='KEY'),
                sg.In('folder', expand_x=True, enable_events=True, key='FOLDER'),
                sg.FolderBrowse()
            ],
            [sg.Listbox([key + ': ' + self.app.model_list[key] for key in self.app.model_list.keys()], size=(20, 16), expand_x=True, enable_events=True, key='VOICES')]
        ]
        tabs = sg.TabGroup([[
            sg.Tab('Queue', queue_control),
            sg.Tab('Speakers', model_control)
        ]], expand_x=True)

        message=[
            sg.Push(),
            sg.Text('New Message:'),
            sg.Input(key='MSG'),
            sg.Button('Add Msg', key='ADDMSG')
        ]

        layout=[
            [connection],
            [tabs],
            [message]
        ]

        self.window = sg.Window('Custom TTS', layout, icon='assets/sir.ico', finalize=True)
        self.window['USERNAME'].bind("<Return>", "_Enter")
        self.window['MSG'].bind("<Return>", "_Enter")

        self.refresh_thread = threading.Thread(target=self.refresh_queue, daemon=True)
        self.refresh_thread.start()

        #Run the window capturing events
        while True:
            event, values = self.window.read()

            # Standard operations
            if event in (None, sg.WINDOW_CLOSED, 'Quit', 'Exit'):
                if self.listener != ():
                    asyncio.run(self.app.kill(self.listener))
                break;

            # App operations
            elif event in ('Connect', 'USERNAME_Enter'):
                if values['USERNAME'] != '':
                    try:
                        self.app.set_channel(values['USERNAME'])
                        threading.Thread(target=self.app.worker, daemon=True).start()
                        self.listener = asyncio.run(self.app.run())
                    except:
                        sg.popup(f'Failed to connect to user. Please try again.', title='Connection Failed')
                else:
                    sg.popup(f'You must enter a Twitch Username', title='Missing Data')
            elif event == 'PAUSE':
                self.app.pause_flag = not self.app.pause_flag
                self.window['PAUSE'].update('Play' if self.app.pause_flag else 'Pause')
            elif event == 'CLEAR':
                self.clear_queue()
            elif event in ('ADDMSG', 'MSG_Enter'):
                if values['MSG'] != '':
                    data = {'bits_used': 1, 'user_name': 'hannah_gbs', 'chat_message': values['MSG']}
                    self.app.tts_queue.put(data)
                    self.window['MSG'].update('');
            elif event == 'ADDVOICE':
                if values['KEY'] != '' and values['FOLDER'] != '':
                    try:
                        self.app.add_model(values['KEY'], values['FOLDER'])
                        dst = os.path.join(self.model_path, 'tts_models--multilingual--multi-dataset--' + values['KEY'] + '/')
                        distutils.dir_util.copy_tree(os.path.dirname(values['FOLDER']), dst)
                        self.window['KEY'].update('')
                        self.window['FOLDER'].update('')
                        self.window['VOICES'].update([key + ': ' + self.app.model_list[key] for key in self.app.model_list.keys()])
                    except Exception as e:
                        sg.popup(f'Failed to create the model: \n' + str(e))
                else:
                    sg.popup(f'You\'re missing either a keyword or folder.')

        self.window.close()

    def refresh_queue(self):
        while True:
            # Update connection status
            try:
                if self.listener:
                    self.status = 'assets/green.png' if self.listener[1].is_connected() else 'assets/red.png'
                    self.window['STATUS'].update(self.status)

                # Collect messages
                with self.app.tts_queue.mutex:
                    messages = [item['user_name'] + ': ' + item['chat_message'] for item in list(self.app.tts_queue.queue)]
                    if messages != self.current_queue_list:
                        self.current_queue_list = messages
                        self.window['QUEUE'].update(self.current_queue_list)

                time.sleep(0.5)
            except:
                print(f'Error updating the connection status and queue...')

    def clear_queue(self):
        was_paused = self.app.pause_flag
        self.app.pause_flag = True
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