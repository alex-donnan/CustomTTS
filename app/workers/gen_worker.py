from actions import *

import queue
import torch.multiprocessing as mp

class genWorker(mp.Process):
	def __init__(self, gen_queue, tts_queue, config, actions):
		mp.Process.__init__(self)
		self.gen_queue = gen_queue
		self.tts_queue = tts_queue
		self.config = config
		self.actions = actions

	def run(self):
		while True:
			try:
				next = self.gen_queue.get(timeout=1)
				if next is None:
					break

				self.generate(next)
			except (queue.Empty, IndexError):
				continue
		
	def generate(self, message_list):
		audio_list = []
		for msg in message_list:
			try:
				msg_obj = self.actions[msg['type']].generate(msg)
				if bool(msg_obj):
					audio_list.append(msg_obj)
			except Exception as e:
				print(f'Failed to generate audio, aborting message: {e}')
				break

		if len(audio_list) > 0:
			self.tts_queue.put(audio_list)
		return