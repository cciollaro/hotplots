import logging
import time

from hotplots.hotplots_io import HotplotsIO
from hotplots.hotplots import Hotplots
from hotplots.hotplots_logging import HotplotsLogging

def main():
    hotplots_io = HotplotsIO()

    # TODO get config filename from commandline args
    config = hotplots_io.load_config_file("config-example.yaml")
    HotplotsLogging.initialize_logging(config.logging)

    hotplots = Hotplots(config, hotplots_io)

    while True:
        try:
            hotplots.run()
        except Exception:
            logging.exception("error while running hotplots")

        logging.info("sleeping %s seconds" % config.source.check_source_drives_sleep_seconds)
        time.sleep(config.source.check_source_drives_sleep_seconds)

if __name__ == '__main__':
    main()
