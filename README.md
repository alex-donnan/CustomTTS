# CustomTTS
#### by Blebs

## Getting started
1. Unzip
2. Install Cuda 13 - must have a device that accepts Cuda 13:
	- https://developer.nvidia.com/cuda-downloads
	- Follow the relevant prompts here
3. Twitch Developer account and App (for ID and Secret)
4. Streamelements account (for Overlay Token)
5. customTTS.exe
6. Hope CUDA isn't borken


## How to use
1. On launch, go to the config tab and fill out relevant fields for each secion
	- General : will need your twitch app ID and secret. you'll need to make a twitch app via their developer page
	- AI : primarily cost
	- Lute : primarily cost
	- Sound : primarily cost
	- TTS : we use the streamelements API. having an account provides you the "overlay token" which works
2. Under *Message Queue*, view chat messages, pause the queue, skip the current message, or clear all.
	- Add a message to the queue with the message entry box at the bottom
3. Under *Speakers*, samples can be added by hitting Load Sample and finding a clear vocal sample of your target voice. 30 seconds is decent, but up to a minute produces good quality audio.
	- Add/Remove will take the 'Keyword' field and the selected sample from the dropdown and make it accessible to your application
4. Under *Sounds*, sounds can be added by hitting Load Sound and finding the sound sample.
	- Add/Remove will take the 'Keyword' field and the selected sound from the dropdown and make it accessible to your application
5. If the volume is too loud, use Windows mixer to modify