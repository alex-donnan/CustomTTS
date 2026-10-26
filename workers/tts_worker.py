from preferredsoundplayer import *
from tts_utils import *

import asyncio
import logging
logger = logging.getLogger(__name__)
import os
import queue
import torch.multiprocessing as mp

class ttsWorker(mp.Process):
	def __init__(self, tts_queue, config_manager, played_file, current_speaker):
		mp.Process.__init__(self, daemon=True)
		self.tts_queue = tts_queue
		self.config_manager = config_manager
		self.played_file = played_file
		self.current_speaker = current_speaker

		# class vars
		self.currently_playing = None

	def run(self):
		while True:
			try:
				if self.config_manager['FLAGS']['pause']: continue

				next = self.tts_queue.get(timeout=1)
				if next is None:
					break

				self.play_audio(next)
			except (queue.Empty, IndexError):
				continue

	# File player
	def play_audio(self, audio_list):
		self.current_speaker.value = b"none"

		soundplay("assets/cheer.wav", block=True)
		sleep(0.25)
		
		media_paused = False
		session = None
		for msg_obj in audio_list:
			logger.info(f'Trying to play {msg_obj['filename']}')

			if not os.path.isfile(msg_obj['filename']): continue

			if msg_obj['type'] == 'LUTE' and self.config_manager['LUTE']['pause_music']:
				session = asyncio.run(get_media_session())
				if session is not None:
					media_paused = session.get_playback_info().playback_status.value == 4
					session.try_pause_async()

			try:
				sound_muted = not self.config_manager[msg_obj['type']]['active']

				if msg_obj['type'] not in self.config_manager['SOUND']['sounds'] and not sound_muted:
					self.current_speaker.value = bytes(msg_obj['type'], 'utf-8')
					sleep(0.5)

				if not sound_muted:
					self.currently_playing = soundplay(msg_obj['filename'])

					while getIsPlaying(self.currently_playing):
						if self.config_manager['FLAGS']['clear'] or self.config_manager['FLAGS']['skip']:
							stopsound(self.currently_playing)
						sleep(0.1)

					stopsound(self.currently_playing)

				self.current_speaker.value = b'none' if not self.config_manager['FLAGS']['pause'] else b'paused'
				os.remove(msg_obj['filename'])
			except Exception as e:
				logger.warn(f'Audio Play failed to play file: {e}')

			# lets the message viewer remove failed messages
			self.played_file.value = bytes(msg_obj['filename'][:-4], 'utf-8')

			if session is not None and media_paused:
				session.try_play_async()
				media_paused = False

		return