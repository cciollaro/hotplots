import glob
import os
import paramiko
import socket
import logging
import subprocess


class Hotplots:
    def __init__(self, config):

        self.config = config

        logging.info("Watching source dirs: ")
        logging.info(self.config.sources())

        logging.info("Considering destinations: ")
        logging.info(self.config.destinations())

    def run(self):
        # load up the status of all of our destinations
        # TODO handle and log case where destination info cannot be loaded
        destinations = [self.get_destination_info(destination_config) for destination_config in self.config.destinations() if destination_config is not None]

        for source_dir in self.config.sources():
            for source_plot_absolute_reference in glob.glob(source_dir + "*.plot"):
                source_plot = {
                    "absolute_reference": source_plot_absolute_reference,
                    "basename": os.path.basename(source_plot_absolute_reference),
                    "size": os.path.getsize(source_plot_absolute_reference),
                    "metadata": self.parse_plot_filename_metadata(source_plot_absolute_reference)
                }

                if not self.is_already_being_transferred(destinations, source_plot):
                    chosen_destination = self.choose_destination(destinations, source_plot)
                    # hacky way to not have to reload destination info
                    chosen_destination["in_flight_transfers"].append(
                        ".%s.xxxxx" % (source_plot["basename"])
                    )
                    self.move_plot(source_plot, chosen_destination)

    def move_plot(self, source_plot, destination):
        if destination["config"]["type"] == "local":
            move_plot_cmd = "rsync -av --remove-source-files %s %s" % (
                source_plot["absolute_reference"], destination["config"]["dir"]
            )
        else:  # remote
            resolved_ip = socket.gethostbyname(destination['config']['hostname'])
            move_plot_cmd = "rsync -av --remove-source-files -e ssh %s %s@%s:%s" % (
                source_plot["absolute_reference"],
                destination["config"]["username"],
                resolved_ip,
                destination["config"]["dir"]
            )

        logging.info("Running move plot command: %s" % move_plot_cmd)
        subprocess.Popen(move_plot_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)

    def choose_destination(self, destinations, source_plot_file):
        destination_filter_fn = lambda d: d["free_bytes"] > source_plot_file["size"] and len(d["in_flight_transfers"]) == 0
        eligible_destinations = list(filter(destination_filter_fn, destinations))

        if len(eligible_destinations) == 0:
            # TODO: handle no eligible destinations
            pass
        else:
            # pick best remaining destination. could be done randomly as well.
            eligible_destinations.sort(key=lambda d: d["free_bytes"], reverse=True)
            return eligible_destinations[0]

    def is_already_being_transferred(self, destinations, source_plot_file):
        for destination in destinations:
            for in_flight_transfer in destination["in_flight_transfers"]:
                in_flight_metadata = self.parse_plot_filename_metadata(in_flight_transfer)
                if source_plot_file["metadata"]["plot_id"] == in_flight_metadata["plot_id"]:
                    return True
        return False

    def get_destination_info(self, destination_config):
        try:
            logging.debug("Loading destination info for %s" % destination_config)
            free_1k_blocks_cmd = "df %s | tail -n 1 | awk '{print $4}'" % (destination_config["dir"])
            in_flight_transfers_cmd = "find %s -name '.*.plot.*'" % (destination_config["dir"])

            if destination_config["type"] == "local":
                free_bytes = int(os.popen(free_1k_blocks_cmd).read().rstrip()) * 1000
                in_flight_transfers_str = os.popen(in_flight_transfers_cmd).read().rstrip()
                if len(in_flight_transfers_str) == 0:
                    in_flight_transfers = []
                else:
                    in_flight_transfers = in_flight_transfers_str.split("\n")
            else:  # remote
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                resolved_ip = socket.gethostbyname(destination_config['hostname'])

                try:
                    client.connect(resolved_ip, port=destination_config['port'], username=destination_config['username'])

                    _, free_1k_blocks_stdout, _ = client.exec_command(free_1k_blocks_cmd)
                    free_bytes = int(free_1k_blocks_stdout.read().decode("utf-8").rstrip()) * 1000

                    _, in_flight_transfers_stdout, _ = client.exec_command(in_flight_transfers_cmd)
                    in_flight_transfers_str = in_flight_transfers_stdout.read().decode("utf-8").rstrip()
                    if len(in_flight_transfers_str) == 0:
                        in_flight_transfers = []
                    else:
                        in_flight_transfers = in_flight_transfers_str.split("\n")
                except Exception as e:
                    raise e
                finally:
                    client.close()

            return {
                "config": destination_config,
                "free_bytes": free_bytes,
                "in_flight_transfers": in_flight_transfers
            }
        except:
            logging.exception("exception trying to load destination info")
            return None

    # parses the metadata out of a plot file name - works for complete
    # plots as well as temporary rsync plots (starting with .)
    def parse_plot_filename_metadata(self, plot_filename):
        basename = os.path.basename(plot_filename)
        if basename.startswith("."):
            # .plot-k32-2021-05-24-12-36-990e8afe5494e4fd91aef0bcd5548f529895400011528e56094c1c3c96edcd27.plot.y29pgW
            _, filename, _, _ = basename.split('.')
        else:
            # plot-k32-2021-05-24-12-36-990e8afe5494e4fd91aef0bcd5548f529895400011528e56094c1c3c96edcd27.plot
            filename, _ = basename.split('.')

        # plot-k32-2021-05-24-12-36-990e8afe5494e4fd91aef0bcd5548f529895400011528e56094c1c3c96edcd27
        _, ksize, year, month, day, hour, minute, plot_id = filename.split('-')

        return {
            "ksize": ksize,
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "plot_id": plot_id
        }