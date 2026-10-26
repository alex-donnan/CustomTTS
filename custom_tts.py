from tts_controller import ttsController
from tts_gui import ttsGui

if __name__ == '__main__':
    controller = ttsController()
    controller.start_workers()
    window = ttsGui(app=controller)