import logging
import random
from dataclasses import dataclass
from enum import Enum

#TODO: when doing math to decide whether to start another transfer, always use a sizeable safety buffer..
# an incorrect "not eligible" is better than an incorrect "eligible" because we we'll freeze up multiple transfers
# in the "not eligible" case, but in the "eligible" case it'll be corrected once the current transfer
# finishes.
from typing import List

from hotplots.hotplots_config import HotplotsConfig
from hotplots.models import SourceInfo, LocalTargetsInfo, RemoteTargetsInfo, SourcePlot, HotPlot, HotPlotTargetDrive

# https://github.com/Chia-Network/chia-blockchain/wiki/k-sizes#storage-requirements
PLOT_BYTES_BY_K = {
    32: 108_880_000_000,  # 101.4 GiB
    33: 224_200_000_000,  # 208.8 GiB
    34: 461_490_000_000,  # 429.8 GiB
    35: 949_300_000_000   # 884.1 GiB
}

class HotplotsEngine:
    # for simplicity, either all actions are going to be movements, or all actions are going to be plot_replacement.
    # that means to start plot_replacement we're going to wait until we have a run which starts when all drives are
    # full or being filled.
    # this means if you have multiple hot plots, one of which will fill a drive and the rest of which will need
    # plot_replacement, then it won't be until next run that the plot_replacement actions are produced.
    @staticmethod
    def get_actions(
            config: HotplotsConfig,
            source_info: SourceInfo,
            local_targets_info: LocalTargetsInfo,
            remote_targets_info: RemoteTargetsInfo
    ):
        # First, get our active transfers into a friendlier format.
        active_transfers_map = HotplotsEngine.build_active_transfers_map(local_targets_info, remote_targets_info)

        ranked_hot_plots = HotplotsEngine.get_ranked_hot_plots(config, source_info, active_transfers_map)

        if not ranked_hot_plots:
            logging.info("No hot plots or they're all being transferred already")
            return

        # Step 1. Figure out all active transfers (and where they're happening

        # Step 1: figure out if we have any hot plots

        # Step 2: figure out if we can transfer it anywhere

        # Step 3: if not, should we delete another plot to make room for it?

        # Step 4: process actions

    @staticmethod
    def get_ranked_hot_plots(
            config: HotplotsConfig,
            source_info: SourceInfo,
            active_transfers_map
    ) -> List[HotPlot]:
        """
        Rank the source plots in order we should move them, according to the configured selection_strategy.
        """
        hot_plots = []
        source_drive_bytes_in_flight = {}
        source_drive_bytes_in_flight.setdefault(0)
        for source_drive_info in source_info.source_drive_infos:
            for source_plot in source_drive_info.source_plots:
                if source_plot.plot_name_metadata.plot_id in active_transfers_map:
                    logging.info("plot %s already in flight" % source_plot.plot_name_metadata.plot_id)
                    source_drive_bytes_in_flight[source_drive_info.source_drive_config] += source_plot.size
                else:
                    hot_plots.append(HotPlot(source_drive_info, source_plot))


        # Build a map so we can easily sort by order appearing in config
        source_drive_info_config_order_lookup = {}
        i = 0
        for source_drive_config in config.source.drives:
            source_drive_info_config_order_lookup[source_drive_config] = i
            i += 1

        # TODO: test ordering here, might need to add a negative sign to get desired orderings
        #       or might want to move sorting inside here so I can just do reverse=true
        def sort_by_criteria(hot_plot: HotPlot):
            if config.source.selection_strategy == "plot_with_oldest_timestamp":
                m = hot_plot.source_plot.plot_name_metadata
                return m.year, m.month, m.day, m.hour, m.minute
            elif config.source.selection_strategy == "drive_with_least_space_remaining":
                bytes_in_flight = source_drive_bytes_in_flight[hot_plot.source_drive_info.source_drive_config]
                return hot_plot.source_drive_info.free_bytes + bytes_in_flight
            elif config.source.selection_strategy == "drive_with_lowest_percent_space_remaining":
                bytes_in_flight = source_drive_bytes_in_flight[hot_plot.source_drive_info.source_drive_config]
                return hot_plot.source_drive_info.total_bytes / (hot_plot.source_drive_info.free_bytes + bytes_in_flight)
            elif config.source.selection_strategy == "config_order":
                return source_drive_info_config_order_lookup[hot_plot.source_drive_info.source_drive_config]
            elif config.source.selection_strategy == "random":
                return random.random()

        sorted_hot_plots = []
        while hot_plots:
            best_hot_plot: HotPlot = sorted(hot_plots, key=sort_by_criteria).pop(0)
            sorted_hot_plots.append(best_hot_plot)
            source_drive_bytes_in_flight[best_hot_plot.source_drive_info.source_drive_config] += best_hot_plot.source_plot.size

        return sorted_hot_plots

    @staticmethod
    def get_source_target_pairings(
            config: HotplotsConfig,
            ranked_hot_plots: List[HotPlot],
            local_targets_info: LocalTargetsInfo,
            remote_targets_info: RemoteTargetsInfo
    ):
        """
        This method needs to know which hot_plot it's considering moving to know how much space to check for.
        :return:
        """
        # an eligible destination is one which is not frequency capped and has enough space for a plot
        # in order to determine if a drive has enough space, we will need to check its in flight transfers
        # we will need to use the ksize from the in-flight file to estimate how much space it will take up when done
        # and we should add a safety margin of some percentage

        hot_plot_target_drives = []
        target_drive_bytes_in_flight = {}
        target_drive_bytes_in_flight.setdefault(0)
        target_host_transfers_in_flight = {}
        target_host_transfers_in_flight.setdefault(0)
        target_drive_transfers_in_flight = {}
        target_drive_transfers_in_flight.setdefault(0)

        for target_drive_info in local_targets_info.target_drive_infos:
            for in_flight_transfer in target_drive_info.in_flight_transfers:
                target_host_and_drive_configs = (local_targets_info.local_host_config, target_drive_info.target_drive_config)
                target_host_transfers_in_flight[local_targets_info.local_host_config] += 1
                target_drive_bytes_in_flight[target_host_and_drive_configs] += 1
                target_drive_bytes_in_flight[target_host_and_drive_configs] += PLOT_BYTES_BY_K[in_flight_transfer.plot_name_metadata.k]


            hot_plot_target_drive = HotPlotTargetDrive(
                local_targets_info.local_host_config,
                target_drive_info
            )
            hot_plot_target_drives.append(hot_plot_target_drive)

        for remote_host_info in remote_targets_info.remote_host_infos:
            for target_drive_info in remote_host_info.target_drive_infos:
                for in_flight_transfer in target_drive_info.in_flight_transfers:
                    target_host_and_drive_configs = (remote_host_info.remote_host_config, target_drive_info.target_drive_config)
                    target_host_transfers_in_flight[remote_host_info.remote_host_config] += 1
                    target_drive_bytes_in_flight[target_host_and_drive_configs] += 1
                    target_drive_bytes_in_flight[target_host_and_drive_configs] += PLOT_BYTES_BY_K[in_flight_transfer.plot_name_metadata.k]

                hot_plot_target_drive = HotPlotTargetDrive(
                    remote_host_info.remote_host_config,
                    target_drive_info
                )
                hot_plot_target_drives.append(hot_plot_target_drive)


        pairings = []
        unpaired_hot_plots = []
        # if there are hot plots left over there is a subtle case I need to check for:
        # are they left over because of frequency capping, but once that clears there's still room
        # for plots? or do we need to transition to plot_replacement for them?

        # for each iteration of this for loop, I need to produce either a pairing or an unpaired_hot_plot.
        # each unpaired_hot_plot should come with the reason it was unpaired (all drives capped, or all drives full)
        for hot_plot in ranked_hot_plots:
            frequency_capped_hot_plot_target_drives = []
            filled_hot_plot_target_drives = []
            eligible_target_drives = []

            for hot_plot_target_drive in hot_plot_target_drives:
                if random.random() > 0.5: # TODO: is_frequency_capped?
                    frequency_capped_hot_plot_target_drives.append(hot_plot_target_drive)
                elif random.random() > 0.5: # TODO: does not have space when considering active transfers
                    filled_hot_plot_target_drives.append(hot_plot_target_drive)
                else:
                    eligible_target_drives.append(hot_plot_target_drive)

            # now we know which drives are eligible for this plot, it's time to sort them by selection
            # strategy (both the prefer_local, and the limits in config)
            if eligible_target_drives:
                ranked_eligible_target_drives = sorted(eligible_target_drives) # TODO
                # add the pairing
            elif frequency_capped_hot_plot_target_drives:
                # in this case we're frequency capped
                # add the unpaired_hot_plot
                pass
            else:
                # in this case, all drives were filled
                # TODO: if somehow hot_plot_target_drives was empty, then we'd land in this else case..
                #   maybe that doesn't matter but might be good go guard anyway since we're talking about
                #   the case that leads to plot replacement
                # add the unpaired hotplot with reason "no room"
                pass





    @staticmethod
    def is_frequency_capped(
            config: HotplotsConfig,
            hot_plot_target_drive: HotPlotTargetDrive,
            target_host_transfers_in_flight,
            target_drive_transfers_in_flight

    ):
        pass # TODO

    @staticmethod
    def is_full(
            hot_plot: HotPlot,
            config: HotplotsConfig,
            hot_plot_target_drive: HotPlotTargetDrive,
            target_drive_bytes_in_flight
    ):
        pass # TODO


    #TODO fix variable names here
    @staticmethod
    def build_active_transfers_map(local_targets_info: LocalTargetsInfo, remote_targets_info: RemoteTargetsInfo):
        # plot_id -> (HostConfig, TargetDriveConfig) (if can also differentiate host)
        active_transfers_map = {}
        for x in local_targets_info.target_drive_infos:
            for y in x.in_flight_transfers:
                active_transfers_map[y.plot_name_metadata.plot_id] = (local_targets_info.local_host_config, x.target_drive_config, y)

        for x in remote_targets_info.remote_host_infos:
            for y in x.target_drive_infos:
                for z in y.in_flight_transfers:
                    active_transfers_map[z.plot_name_metadata.plot_id] = (x.remote_host_config, y.target_drive_config, z)

        return active_transfers_map

@dataclass
class GetTransferActionsResult:
    pass

@dataclass
class GetTransferActionResultStatus(Enum):
    pass
