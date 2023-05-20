# CustomTTS
#### by Blebs

## Getting started
1. Unzip
2. ttsGui.exe

## Changes (idfk it works)
1. pip reinstall librosa, decorator, audioread, unidic_lite
2. Additional hook for librosa, maybe TTS, trainer, and gruut
	- Librosa needs explicit .core addition
	- TTS, trainer, gruut all got hardcoded versions in ```__init__.py```
3. Modify TTs/tts/layers/generic/wavenet.py decorator at 5 to ```@torch.jit._script_if_tracing```
4. Add TTS to the PATH, cause why not. Or figure out how to ```pip install -e TTS``` without setup.py
5. auto-py-to-exe, Settings > Import Config from pyinstaller.JSON
6. Build
7. In output > ttsGui > librosa.__init__.pyi add:
	```
		from .core import (
			magphase as magphase,
			pyin as pyin
		)
	```
	Compile to .pyc, replace
8. In output > ttsGui > TTS move the configs to a new folder tts
9. ???
10. Profit

## How to use
1. On launch enter Twitch username and hit connect to authenticate the program with your Twitch account
2. Under *Message Queue*, view chat messages, pause the queue, or clear all.
	- More to come
3. Add a message to the queue with the message entry box at the bottom
4. Under *Voices*, add models by keyword and folder
	- The keyword should be distinct, adding a duplicate will *overwrite* previous keywords
	- Models folders should be the name of the person it was trained on for clarity
5. If the volume is too loud, use Windows mixer to modify
	- We might, one day, eventually, change this