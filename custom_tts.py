import logging
import torch.multiprocessing as mp
from tts_controller import ttsController
from tts_gui import ttsGui
from logger_config import setup_logging

if __name__ == '__main__':
    # start logging
    setup_logging()
    logger = logging.getLogger('main')

    # MP freeze
    mp.freeze_support()
    
    controller = ttsController()
    controller.start_workers()
    window = ttsGui(app=controller)