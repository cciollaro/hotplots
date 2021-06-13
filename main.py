import logging
import time

from hotplots.fs_access import HotplotsIO
from hotplots.hotplots import Hotplots
from hotplots.hotplots_logging import HotplotsLogging

# TODO `verify` that just tests touching and deleting a small file to each destination and outputs results
#   checks if rsync is installed
#   checks if progress is installed
#   could even run it on startup (conditionally)
if __name__ == '__main__':
    # use real filesystem access
    fs_access = HotplotsIO()

    # TODO make config filename configurable?
    config = fs_access.load_config_file("config-example.yaml")
    HotplotsLogging.initialize_logging(config.logging)

    hotplots = Hotplots(config, fs_access)

    while True:
        try:
            hotplots.run()
        except Exception:
            logging.exception("error while running hotplots")

        logging.info("sleeping %s seconds" % config.source.check_source_drives_sleep_seconds)
        time.sleep(config.source.check_source_drives_sleep_seconds)
