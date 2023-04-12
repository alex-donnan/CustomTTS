import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror

import asyncio
import queue
import threading
import ttsController as TTS


class ttsGui(tk.Tk):
    def __init__(self, app: TTS):
        # TKinter setup
        super().__init__()

        # TTS Controller
        self.app = app
        self.listener = ()

        def set_listener(listener: tuple):
            self.listener = listener

        self.queue = queue.Queue()

        # Frames  
        self.wm_title("Custom TTS")
        frm_queue = ttk.Frame(self, padding=10)
        frm_start = ttk.Frame(self, padding=10)

        # Queue frame
        ttk.Label(frm_queue, text="Queued TTS Messages").grid(column=0, row=0, columnspan=4)
        queueView = tk.Listbox(frm_queue, height=10)
        queueView.grid(column=0, row=1, columnspan=4)

        # Start frame
        frm_start.grid()
        ttk.Label(frm_start, text="Enter Twitch username to authorize: ").grid(column=0, row=0)
        channel_entry = ttk.Entry(frm_start)
        channel_entry.insert(0, self.app.get_channel())
        channel_entry.grid(column=1, row=0)

        def channel_entry_cmd():
            if channel_entry.get() != "":
                self.app.set_channel(channel_entry.get())
                threading.Thread(target=self.app.worker, daemon=True).start()
                set_listener(asyncio.run(self.app.run()))
                frm_queue.grid()
                frm_start.grid_forget()
            else:
                showerror(title='Error', message='You must enter a Twitch Username')

        ttk.Button(
            frm_start,
            text="Connect to Twitch",
            command=channel_entry_cmd
        ).grid(column=0, row=2, columnspan=2, sticky=tk.E)

    def on_closing(self):
        if self.listener != ():
            asyncio.run(self.app.kill(self.listener))
        self.destroy()


if __name__ == "__main__":
    controller = TTS.ttsController()
    window = ttsGui(app=controller)
    window.protocol("WM_DELETE_WINDOW", window.on_closing)
    window.mainloop()
