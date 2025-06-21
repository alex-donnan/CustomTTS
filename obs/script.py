import asyncio
import threading

import obspython as obs
import websockets
import winrt.windows.media.control as wmc


class Hotkey:
    def __init__(self, callback, obs_settings, _id, _name):
        self.obs_data = obs_settings
        self.hotkey_id = obs.OBS_INVALID_HOTKEY_ID
        self.hotkey_saved_key = None
        self.callback = callback
        self._id = _id
        self._name = _name

        self.load_hotkey()
        self.register_hotkey()
        self.save_hotkey()

    def register_hotkey(self):
        self.hotkey_id = obs.obs_hotkey_register_frontend(
            "htk_id" + str(self._id), self._name, self.callback
        )
        obs.obs_hotkey_load(self.hotkey_id, self.hotkey_saved_key)
        print("hotkey registered")

    def load_hotkey(self):
        self.hotkey_saved_key = obs.obs_data_get_array(
            self.obs_data, "htk_id" + str(self._id)
        )
        obs.obs_data_array_release(self.hotkey_saved_key)
        print("hotkey loaded")

    def save_hotkey(self):
        self.hotkey_saved_key = obs.obs_hotkey_save(self.hotkey_id)
        obs.obs_data_set_array(
            self.obs_data, "htk_id" + str(self._id), self.hotkey_saved_key
        )
        obs.obs_data_array_release(self.hotkey_saved_key)


async def get_media_session():
    sessions = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = sessions.get_current_session()
    return session


async def pause_media():
    session = await get_media_session()
    media_paused = False
    if session is not None:
        media_paused = session.get_playback_info().playback_status.value == 4
        session.try_pause_async()
    return media_paused


async def resume_media():
    session = await get_media_session()
    if session is not None:
        session.try_play_async()


class websocketServer:
    def __init__(self, settings):
        self.websocket_server = None
        self.websocket_server_thread = threading.Thread(target=self.start_websocket_server, daemon=True)
        self.websocket_server_thread.start()
        self.media_paused = False

    async def websocket_server_worker(self, websocket_server):
        self.websocket_server = websocket_server
        while True:
            try:
                client_message = await websocket_server.recv()
            except:
                print("Websocket server connection terminated")
                break

            response = None
            if client_message == "Connect":
                response = "Connected"
                print("Client connected, sending connection response.")
            if client_message == "pause":
                self.media_paused = await pause_media()
                print("Pausing music")
            if client_message == "resume":
                if self.media_paused:
                    await resume_media()
                    print("Resuming music")
                self.media_paused = False

            if response:
                try:
                    await websocket_server.send(response)
                except websockets.ConnectionClosed:
                    print("Websocket server connection terminated")
                    break

    def start_websocket_server(self):
        print("Starting websocket server")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run_server():
            async with websockets.serve(self.websocket_server_worker, 'localhost', 1515):
                await asyncio.Future()

        loop.run_until_complete(run_server())

    async def skip_tts(self):
        print("Skipping TTS")
        try:
            await self.websocket_server.send("skip")
        except websockets.ConnectionClosed:
            print("Websocket server connection terminated")


class h:
    htk_copy = None


websocket_server = None
skip_hotkey = h()


def skip_tts(pressed):
    global websocket_server
    if pressed and isinstance(websocket_server, websocketServer):
        asyncio.run(websocket_server.skip_tts())


def script_load(settings):
    global websocket_server
    websocket_server = websocketServer(settings)
    skip_hotkey.htk_copy = Hotkey(skip_tts, settings, "skip_tts_key", "Skip TTS")


def script_save(settings):
    skip_hotkey.htk_copy.save_hotkey()


def script_unload():
    obs.obs_hotkey_unregister(skip_hotkey.htk_copy)