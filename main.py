import logging
import time

import yaml

from hotplots import Hotplots
from hotplots_config import HotplotsConfig

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
