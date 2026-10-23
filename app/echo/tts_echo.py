from .inference import (
	load_model,
	load_fish_ae,
	load_pca_state,
	load_audio,
	sample_pipeline,
	sample_euler_cfg_independent_guidances
)
from functools import partial
import gc
import json
import time
import torchaudio
import torch

class ttsEcho:
	def __init__(self, app):
		self.app = app

		# check for cuda
		self.device = "cuda" if torch.cuda.is_available() else "cpu"
		print(f"Using device: {self.device}")

		# load local inf models
		self.model = load_model(
			path="./echo/models/echo/pytorch_model.safetensors",
			delete_blockwise_modules=True,
			device=self.device
		)
		self.fish_ae = load_fish_ae(
			path="./echo/models/fish/pytorch_model.safetensors",
			dtype=torch.bfloat16,
			device=self.device
		)
		self.pca_state = load_pca_state(
			path="./echo/models/echo/pca_state.safetensors",
			device=self.device
		)

		# configure sampler
		self.sample_fn = partial(
			sample_euler_cfg_independent_guidances,
			num_steps=20,
			cfg_scale_text=3.0,
			cfg_scale_speaker=8.0,
			cfg_min_t=0.5,
			cfg_max_t=1.0,
			truncation_factor=None,
			rescale_k=None,
			rescale_sigma=None,
			speaker_kv_scale=None,
			speaker_kv_max_layers=None,
			speaker_kv_min_t=None,
			sequence_length=640, # (~30 seconds)
		)

		self.speaker_samples = eval(self.app.config['AI']['speakers'])
		self.speaker_audio = {}
		for speaker in self.speaker_samples.keys():
			audio = load_audio(self.app.config['AI']['samplesdir'] + self.speaker_samples[speaker])
			if self.device == "cuda":
				audio.cuda()
			self.speaker_audio[speaker] = audio

		print('Echo: Loaded models and PCA state')
		print(f'Echo: Loaded {len(self.speaker_audio)} voices')

	def unload_models(self):
		del self.model
		del self.fish_ae
		del self.pca_state
		del self.sample_fn

		gc.collect()

		if self.device == 'cuda':
			torch.cuda.empty_cache()
			torch.cuda.ipc_collect()

	def add_speaker(self, name, filename):
		self.speaker_samples[name] = self.app.config['AI']['samplesdir'] + filename
		if name not in self.speaker_audio.keys():
			audio = load_audio(self.speaker_samples[name])
			if self.device == "cuda":
				audio.cuda()
			self.speaker_audio[name] = audio

	def remove_speaker(self, name):
		if name in self.speaker_samples.keys():
			del self.speaker_samples[name]

		if name in self.speaker_audio.keys():
			del self.speaker_audio[name]

		self.app.config.set('AI', 'speakers', json.dumps(self.speaker_samples))
		self.app.save_config()

	def generate(self, name, text, filename):
		if text[0:4] != '[S1]':
			text = '[S1] ' + text

		try:
			start_time = time.time()
			audio_out, _ = sample_pipeline(
				model=self.model,
				fish_ae=self.fish_ae,
				pca_state=self.pca_state,
				sample_fn=self.sample_fn,
				text_prompt=text,
				speaker_audio=self.speaker_audio[name],
				rng_seed=0,
			)

			torchaudio.save(filename, audio_out[0].cpu(), 44100)
			end_time = time.time() - start_time
			print(f'Local generation succeeded in {end_time:.6f} seconds')
		except Exception as e:
			print(f'Local generation failed: {e}')
			return False

		return True