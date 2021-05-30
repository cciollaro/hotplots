import logging
import time

import desert
import yaml

from hotplots.hotplots import Hotplots
from hotplots.hotplots_config import HotplotsConfig
from hotplots.hotplots_logging import HotplotsLogging

# TODO `verify` that just tests writing and deleting a small file to each destination and outputs results
#   checks if rsync is installed
#   checks if progress is installed
#   could even run it on startup (conditionally)
if __name__ == '__main__':
    # TODO make config filename configurable?
    config = HotplotsConfig.load_config_file("config-example.yaml")
    HotplotsLogging.initialize_logging(config.logging)
    hotplots = Hotplots(config)

    while True:
        try:
            hotplots.run()
        except Exception:
            logging.exception("error while running hotplots")

        logging.info("sleeping %s seconds" % config.source.check_source_drives_sleep_seconds)
        time.sleep(config.source.check_source_drives_sleep_seconds)
