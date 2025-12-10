# CustomTTS
#### by Blebs

## Getting started
1. Unzip
2. ttsGui.exe

## Changes (idfk it works)
In .venv -
1. pip install auto-py-to-exe, requirements.txt
2. Modify TTs/tts/layers/generic/wavenet.py decorator at 5 to ```@torch.jit._script_if_tracing```
3. auto-py-to-exe, Settings > Import Config from pyinstaller.JSON
4. Build
5. Add source folder ```inflect``` from .venv/Lib/ into ```_include``` folder
6. TTS, gruut got hardcoded versions in output (can just add VERSION in named folder)
7. In output > ttsGui > TTS move the configs to a new folder tts
8. ???
9. Profit

## Models
If you are creating a new model, please ensure the following:
1. Files are named as such:
	- model_file.pth
	- speakers.pth
	- config.json
	- language_ids.json
	TODO: Generalize
2. config.json must use relative paths for speakers and languages
	- ./models/NAMEOFMODEL/FILENAME
	TODO: Auto update

## How to use
1. On launch enter Twitch username and hit connect to authenticate the program with your Twitch account
2. Under *Message Queue*, view chat messages, pause the queue, or clear all.
	- More to come
3. Add a message to the queue with the message entry box at the bottom
4. Under *Voices*, add models by keyword and folder
	- The keyword should be distinct, adding a duplicate will not overwrite previous keywords
	- Models folders should be the name of the person it was trained on for clarity
5. If the volume is too loud, use Windows mixer to modify
	- We might, one day, eventually, change this