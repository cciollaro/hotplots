import glob
import os
import paramiko
import socket
import logging
import subprocess
import psutil
import contextlib
from hotplots.fs_access import FSAccess
from hotplots.hotplots_config import HotplotsConfig
from hotplots.hotplots_engine import HotplotsEngine
from hotplots.models import SourceInfo


class Hotplots:
    def __init__(self, config: HotplotsConfig):
        self.config = config

        # cache of target_config -> plot absolute reference -> memo data to avoid unnecessary disk reads
        self.memo_cache = {}

        # don't have to check drives that are full
        self.full_target_drives_cache = {}

    # NOTE: for k=32 plot size let's assume: 101.4 GiB (108.9 GB)
    def run(self):
        # First check all sources to see if there are any plots at all
        source_info: SourceInfo = FSAccess.get_source_info(self.config.source)

        # If no plot files, there's nothing to do
        if all([not s.source_plots for s in source_info.source_drive_infos]):
            logging.info("Found no plot files")
            # TODO: uncomment
            # return

        # Next, let's fetch disk space and in-progress transfer information from all targets
        # These are fairly light operations, and provides all the info we need to know if we can
        # perform a simple transfer.
        local_targets = FSAccess.get_local_target_info(self.config.targets.local)
        remote_targets = FSAccess.get_remote_target_info(self.config.targets.remote)


        # possible results:
        # - all_possible_transfers_are_in_progress
        # - drives_eligible_but_rate_limited
        # - transfers_requested
        # - all_drives_full
        #   - this will be the case when


        # another stab at possible results:
        # - NOOP (either all plots already being moved, or we're rate limited)
        # - TRANSFERS (contains the transfers to be performed)
        # - ELIGIBLE_DRIVES_ARE_BUSY
        # - NO_ELIGIBLE_DRIVES
        # TODO: in order to
        # get_transfer_actions_result = HotplotsEngine.get_transfer_actions(source_plots, local_targets, remote_targets)

        # drives have free_bytes and effective_free_bytes..

        # In the case where some transfers are possible, and then after that we'd start replacing plots



        # FSAccess.process_actions(actions)


        # for source_dir in self.config.sources():
        #     for source_plot_absolute_reference in glob.glob(source_dir + "*.plot"):
        #
        #         source_plot = {
        #             "absolute_reference": source_plot_absolute_reference,
        #             "basename": os.path.basename(source_plot_absolute_reference),
        #             "size": os.path.getsize(source_plot_absolute_reference),
        #             "metadata": self.parse_plot_filename_metadata(source_plot_absolute_reference)
        #         }
        #
        #         if not self.is_already_being_transferred(destinations, source_plot):
        #             chosen_destination = self.choose_destination(destinations, source_plot)
        #             # hacky way to not have to reload destination info - we want to exclude this destination
        #             # in case there are more plots to be transferred in this `run`.
        #             chosen_destination["in_flight_transfers"].append(
        #                 ".%s.xxxxx" % (source_plot["basename"])
        #             )
        #             self.move_plot(source_plot, chosen_destination)

    # def is_already_being_transferred(self, destinations, source_plot_file):
    #     for destination in destinations:
    #         for in_flight_transfer in destination["in_flight_transfers"]:
    #             in_flight_metadata = self.parse_plot_filename_metadata(in_flight_transfer)
    #             if source_plot_file["metadata"]["plot_id"] == in_flight_metadata["plot_id"]:
    #                 return True
    #     return False

    @staticmethod
    def choose_destination(destinations, source_plot_file):
        destination_filter_fn = lambda d: d["free_bytes"] > source_plot_file["size"] and len(d["in_flight_transfers"]) == 0
        eligible_destinations = list(filter(destination_filter_fn, destinations))

        if len(eligible_destinations) == 0:
            # TODO: handle no eligible destinations
            pass
        else:
            # pick best remaining destination. could be done randomly as well.
            eligible_destinations.sort(key=lambda d: d["free_bytes"], reverse=True)
            return eligible_destinations[0]


    # @staticmethod
    # def move_plot(source_plot, destination):
    #     if destination["config"]["type"] == "local":
    #         move_plot_cmd = "rsync -av --remove-source-files %s %s" % (
    #             source_plot["absolute_reference"], destination["config"]["dir"]
    #         )
    #     else:  # remote
    #         resolved_ip = socket.gethostbyname(destination['config']['hostname'])
    #         move_plot_cmd = "rsync -av --remove-source-files -e ssh %s %s@%s:%s" % (
    #             source_plot["absolute_reference"],
    #             destination["config"]["username"],
    #             resolved_ip,
    #             destination["config"]["dir"]
    #         )
    #
    #     logging.info("Running move plot command: %s" % move_plot_cmd)
    #     subprocess.Popen(move_plot_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)


    # @staticmethod
    # def count_running_rsyncs():
    #     jobs = 0
    #     for proc in psutil.process_iter(['pid', 'name']):
    #         with contextlib.suppress(psutil.NoSuchProcess):
    #             if proc.name() == 'rsync':
    #                 jobs += 1
    #                 # TODO - should we be more specific about which rsyncs count
    #                 # args = proc.cmdline()
    #                 # for arg in args:
    #                 #     if arg.startswith(dest):
    #                 #         jobs.append(proc.pid)
    #     return jobs
