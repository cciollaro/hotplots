import hotplots
import time
import yaml
import logging

from hotplots_config import HotplotsConfig
from hotplots import Hotplots

# move this directory to my plotter (for development):
# rsync -alPvz /Users/cciollaro/PycharmProjects/hotplots cc@cc-desktop-linux.local:/home/cc
# rm -rf venv
# python3 -m venv venv
# . ./venv/bin/activate
# pip install -r requirements.txt
# python main.py
if __name__ == '__main__':
    logging.basicConfig(filename='hotplots.log', level=logging.DEBUG) # TODO: figure out why encoding='utf-8' doesn't work on linux/py3.8

    with open("config.yaml", 'r') as stream:
        data_loaded = yaml.safe_load(stream)

    config = HotplotsConfig(data_loaded)
    hotplots = Hotplots(config)

    while True:
        try:
            hotplots.run()
        except:
            logging.exception("error while running hotplots")
        # TODO configurable
        logging.info("sleeping 60s")
        time.sleep(60)
