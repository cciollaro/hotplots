import logging
import time

from hotplots.hotplots_io import HotplotsIO
from hotplots.hotplots import Hotplots
from hotplots.hotplots_logging import HotplotsLogging

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Hotplots - Chia Plots Archiving Program.')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config file.')
    args = parser.parse_args()

    hotplots_io = HotplotsIO()

    config = hotplots_io.load_config_file(args.config)
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
