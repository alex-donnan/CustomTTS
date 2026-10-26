import logging
import torch.multiprocessing as mp
import sys

from tts_controller import ttsController
from tts_gui import ttsGui
from setup_logging import setup_logging

if __name__ == '__main__':
    if len(sys.argv) > 1:
        debug = True if sys.argv[1] == 'debug' else False
    else:
        debug = False

    # start logging
    setup_logging(debug)
    logger = logging.getLogger('main')

    # MP freeze
    mp.freeze_support()
    
    controller = ttsController()
    controller.start_workers()
    window = ttsGui(app=controller)