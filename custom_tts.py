import logging
import shutil
import os
import torch.multiprocessing as mp
import sys

from tts_controller import ttsController
from tts_gui import ttsGui
from setup_logging import setup_logging

os.environ['HF_HUB_DISABLE_PROCESS_BARS'] = '1'

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

    # check config exists
    if not os.path.exists('config.ini'):
        if os.path.exists('config.ini.example'):
            shutil.copy('config.ini.example', 'config.ini')
        else:
            raise Exception('Config example file missing, aborting')
    
    controller = ttsController()
    controller.start_workers()
    window = ttsGui(app=controller)