import logging
import random
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

#TODO: when doing math to decide whether to start another transfer, always use a sizeable safety buffer..
# an incorrect "not eligible" is better than an incorrect "eligible" because we we'll freeze up multiple transfers
# in the "not eligible" case, but in the "eligible" case it'll be corrected once the current transfer
# finishes.
from typing import List, Union, Tuple, Callable

from hotplots.hotplots_config import HotplotsConfig, RemoteHostConfig, LocalHostConfig, TargetDriveConfig, \
    SourceDriveConfig
from hotplots.models import SourceInfo, LocalTargetsInfo, RemoteTargetsInfo, SourcePlot, HotPlot, HotPlotTargetDrive, \
    TargetsInfo, GetSourceTargetPairingsResult, GetActionsNoActionResult, GetActionsTransfersResult, \
    GetActionsPlotReplacementResult

# https://github.com/Chia-Network/chia-blockchain/wiki/k-sizes#storage-requirements
PLOT_BYTES_BY_K = {
    32: 108_880_000_000,  # 101.4 GiB
    33: 224_200_000_000,  # 208.8 GiB
    34: 461_490_000_000,  # 429.8 GiB
    35: 949_300_000_000   # 884.1 GiB
}

# Since we don't get the disk usage information and the staged plot file size information at the same moment (they're
# done in separate calls), we add a 5% error term to the staged file size as insurance against over-committing a drive
# and filling it up, which is a very bad outcome.
# 5% is not empirically tested at all, it's just a value that I figure should be enough.
# In the case that the 5% causes a false negative, it'll eventually be rectified once transfers on the drive complete,
# which is a much less bad outcome than filling the drive. Reducing the 5% here will reduce the false negative rate, but
# at some point it will introduce false positives (over-commit case) so reduce with caution.
STAGED_FILES_ERROR_TERM = 1.05

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
            targets_info: TargetsInfo
    ):
        # Get all source plots that aren't actively being transferred
        ranked_hot_plots = HotplotsEngine.get_ranked_hot_plots(config, source_info, targets_info.active_transfers_map())

        # Quick short-circuit
        if not ranked_hot_plots:
            logging.info("No hot plots or they're all being transferred already")
            return

        # get the results from the pairing algorithm
        source_target_pairings_result = HotplotsEngine.get_source_target_pairings(config, ranked_hot_plots, source_info, targets_info)

        if source_target_pairings_result.pairings:
            # In the case that pairings were made, we're simply going to execute them and defer other things
            # such as plot replacement to the next invocation.
            return GetActionsTransfersResult(source_target_pairings_result.pairings)
            pass

        elif source_target_pairings_result.unpaired_hot_plots_due_to_capping:
            # If any of our hot plots weren't transferrable because of capping, we'll simply recommend no action
            return GetActionsNoActionResult()

        elif source_target_pairings_result.unpaired_hot_plots_due_to_no_space:
            # In the case that all of our hotplots had nowhere to go, we can recommend plot_replacement for all hot_plots
            return GetActionsPlotReplacementResult(ranked_hot_plots)


    @staticmethod
    def get_ranked_hot_plots(
            config: HotplotsConfig,
            source_info: SourceInfo,
            active_transfers_map: dict[str, Tuple[Union[LocalHostConfig, RemoteHostConfig], TargetDriveConfig]]
    ) -> List[HotPlot]:
        """
        Rank the source plots in order we should move them, according to the configured selection_strategy.
        """
        hot_plots: List[HotPlot] = []
        source_drive_bytes_in_flight: dict[SourceDriveConfig, int] = defaultdict(lambda: 0)

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
        #       or might want to move sorting inside here so it can utilize reverse=true
        def sort_by_criteria(hot_plot: HotPlot):
            selection_strategy = config.source.selection_strategy
            if selection_strategy == "plot_with_oldest_timestamp":
                m = hot_plot.source_plot.plot_name_metadata
                return m.year, m.month, m.day, m.hour, m.minute
            elif selection_strategy == "drive_with_least_space_remaining":
                bytes_in_flight = source_drive_bytes_in_flight[hot_plot.source_drive_info.source_drive_config]
                return hot_plot.source_drive_info.free_bytes + bytes_in_flight
            elif selection_strategy == "drive_with_lowest_percent_space_remaining":
                bytes_in_flight = source_drive_bytes_in_flight[hot_plot.source_drive_info.source_drive_config]
                return hot_plot.source_drive_info.total_bytes / (hot_plot.source_drive_info.free_bytes + bytes_in_flight)
            elif selection_strategy == "config_order":
                return source_drive_info_config_order_lookup[hot_plot.source_drive_info.source_drive_config]
            elif selection_strategy == "random":
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
            source_info: SourceInfo,
            targets_info: TargetsInfo
    ) -> GetSourceTargetPairingsResult:
        """
        This method needs to know which hot_plot it's considering moving to know how much space to check for.
        :return:
        """
        # an eligible destination is one which is not frequency capped and has enough space for a plot
        # in order to determine if a drive has enough space, we will need to check its in flight transfers
        # we will need to use the ksize from the in-flight file to estimate how much space it will take up when done
        # and we should add a safety margin of some percentage

        hot_plot_target_drives: List[HotPlotTargetDrive] = []

        source_drive_transfers_in_flight: dict[SourceDriveConfig, int] = defaultdict(lambda: 0)

        target_host_transfers_in_flight: dict[Union[LocalHostConfig, RemoteHostConfig], int] = defaultdict(lambda: 0)

        target_drive_transfers_in_flight: dict[Tuple[Union[LocalHostConfig, RemoteHostConfig], TargetDriveConfig], int] = defaultdict(lambda: 0)
        # sum total of bytes remaining to be transferred, inferred from the k-size of staged files minus the size of the staged file
        target_drive_committed_bytes: dict[Tuple[Union[LocalHostConfig, RemoteHostConfig], TargetDriveConfig], int] = defaultdict(lambda: 0)

        remote_transfers = 0

        # update state w/ local target info
        target_host_config = targets_info.local_targets_info.local_host_config
        for target_drive_info in targets_info.local_targets_info.target_drive_infos:
            for in_flight_transfer in target_drive_info.in_flight_transfers:
                target_host_transfers_in_flight[target_host_config] += 1

                target_host_and_drive_configs = (target_host_config, target_drive_info.target_drive_config)
                target_drive_committed_bytes[target_host_and_drive_configs] += (PLOT_BYTES_BY_K[in_flight_transfer.plot_name_metadata.k] - in_flight_transfer.current_file_size)

            hot_plot_target_drive = HotPlotTargetDrive(
                target_host_config,
                target_drive_info
            )
            hot_plot_target_drives.append(hot_plot_target_drive)

        # update state w/ remote target info
        for remote_host_info in targets_info.remote_targets_info.remote_host_infos:
            target_host_config = remote_host_info.remote_host_config
            for target_drive_info in remote_host_info.target_drive_infos:
                for in_flight_transfer in target_drive_info.in_flight_transfers:
                    target_host_transfers_in_flight[target_host_config] += 1

                    target_host_and_drive_configs = (target_host_config, target_drive_info.target_drive_config)
                    target_drive_committed_bytes[target_host_and_drive_configs] += (PLOT_BYTES_BY_K[in_flight_transfer.plot_name_metadata.k] - in_flight_transfer.current_file_size)

                hot_plot_target_drive = HotPlotTargetDrive(
                    remote_host_info.remote_host_config,
                    target_drive_info
                )
                hot_plot_target_drives.append(hot_plot_target_drive)

        # update state w/ source drive info
        for source_info in source_info.source_drive_infos:
            for source_plot in source_info.source_plots:
                if source_plot.plot_name_metadata.plot_id in targets_info.active_transfers_map:
                    (host_config, target_drive_config) = targets_info.active_transfers_map()[source_plot.plot_name_metadata.plot_id]
                    if not host_config.is_local():
                        remote_transfers += 1
                    source_drive_transfers_in_flight[source_info.source_drive_config] += 1

        def is_frequency_capped(hot_plot: HotPlot, hot_plot_target_drive: HotPlotTargetDrive):
            """
            The ways that can be frequency capped:
              - max concurrent outbound remote transfers
              - source drive max concurrent outbound transfers
              - target drive max concurrent inbound transfers
            """
            max_concurrent_remote_transfers = config.targets.remote.max_concurrent_outbound_transfers
            if remote_transfers >= max_concurrent_remote_transfers:
                return True

            source_drive_max_concurrent_outbound_transfers = hot_plot.source_drive_info.source_drive_config.max_concurrent_outbound_transfers
            if source_drive_transfers_in_flight[hot_plot.source_drive_info.source_drive_config] >= source_drive_max_concurrent_outbound_transfers:
                return True

            target_drive_max_concurrent_inbound_transfers = hot_plot_target_drive.host_config.max_concurrent_inbound_transfers
            if target_drive_transfers_in_flight[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)] >= target_drive_max_concurrent_inbound_transfers:
                return True

            return False

        def has_enough_space(hot_plot: HotPlot, hot_plot_target_drive: HotPlotTargetDrive):
            # Need to check if the target drive has enough space for the hot_plot, while taking into account
            # active transfers (and some fudge factor because our disk space reading and active transfers size reading
            # don't happen at exactly the same time)
            committed_bytes = (target_drive_committed_bytes[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)] * STAGED_FILES_ERROR_TERM)
            available_bytes = hot_plot_target_drive.target_drive_info.free_bytes - committed_bytes
            if available_bytes >= hot_plot.source_plot.size:
                return True

            return False

        # Build a map so we can easily sort by order appearing in config
        target_drive_config_order_lookup = {}
        i = 0
        for target_drive_config in config.targets.local.drives:
            target_drive_config_order_lookup[target_drive_config] = i
            i += 1

        for remote_host in config.targets.remote.hosts:
            for target_drive_config in remote_host.drives:
                target_drive_config_order_lookup[target_drive_config] = i
                i += 1

        def rank_hot_plot_target_drives(hot_plot_target_drives: List[HotPlotTargetDrive]) -> List[HotPlotTargetDrive]:
            # When sorting target drives, we don't apply the error term to committed bytes.
            # We have a very small chance of choosing a sub-optimal target drive but in that
            # case the options would have to have been effectively equal. It doesn't seem
            # like error terms will really change anything in this scenario.
            def naive_rank_hot_plot_target_drives():
                selection_strategy = config.targets.selection_strategy
                if selection_strategy == "config_order":
                    def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                        return target_drive_config_order_lookup[hot_plot_target_drive.target_drive_info.target_drive_config]
                    return sorted(hot_plot_target_drives, key=key_func)
                elif selection_strategy == "drive_with_least_space_remaining":
                    def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                        return hot_plot_target_drive.target_drive_info.free_bytes - target_drive_committed_bytes[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                    return sorted(hot_plot_target_drives, key=key_func)
                elif selection_strategy == "drive_with_most_space_remaining":
                    def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                        return hot_plot_target_drive.target_drive_info.free_bytes - target_drive_committed_bytes[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                    return sorted(hot_plot_target_drives, key=key_func, reverse=True)
                elif selection_strategy == "drive_with_lowest_percent_space_remaining":
                    def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                        uncommitted_bytes = hot_plot_target_drive.target_drive_info.free_bytes - target_drive_committed_bytes[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                        return uncommitted_bytes / hot_plot_target_drive.target_drive_info.total_bytes
                    return sorted(hot_plot_target_drives, key=key_func)
                elif selection_strategy == "drive_with_highest_percent_space_remaining":
                    def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                        uncommitted_bytes = hot_plot_target_drive.target_drive_info.free_bytes - target_drive_committed_bytes[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                        return uncommitted_bytes / hot_plot_target_drive.target_drive_info.total_bytes
                    return sorted(hot_plot_target_drives, key=key_func, reverse=True)
                elif selection_strategy == "random":
                    return sorted(hot_plot_target_drives, key=lambda x: random.random())

            ranked_hot_plot_target_drives = naive_rank_hot_plot_target_drives()

            if config.targets.target_host_preference == "unspecified":
                return ranked_hot_plot_target_drives

            ranked_local_hot_plot_target_drives = [x for x in ranked_hot_plot_target_drives if x.is_local()]
            ranked_remote_hot_plot_target_drives = [x for x in ranked_hot_plot_target_drives if x.is_local()]

            if config.targets.target_host_preference == "local":
                return ranked_local_hot_plot_target_drives + ranked_remote_hot_plot_target_drives
            elif config.targets.target_host_preference == "remote":
                return ranked_remote_hot_plot_target_drives + ranked_local_hot_plot_target_drives

        pairings = []
        unpaired_hot_plots_due_to_capping = []
        unpaired_hot_plots_due_to_no_space = []

        # Try to find a home for each plot, and if we cannot, add it to the proper collection.
        # If the only results we receive are "due to no space" then we'll conditionally move onto plot replacement.
        for hot_plot in ranked_hot_plots:
            frequency_capped_hot_plot_target_drives = []
            filled_hot_plot_target_drives = []
            eligible_target_drives = []

            for hot_plot_target_drive in hot_plot_target_drives:
                if is_frequency_capped(hot_plot, hot_plot_target_drive):
                    frequency_capped_hot_plot_target_drives.append(hot_plot_target_drive)
                elif not has_enough_space(hot_plot, hot_plot_target_drive):
                    filled_hot_plot_target_drives.append(hot_plot_target_drive)
                else:
                    eligible_target_drives.append(hot_plot_target_drive)

            if eligible_target_drives:
                ranked_eligible_target_drives = rank_hot_plot_target_drives(eligible_target_drives)
                selected_hot_plot_target_drive = ranked_eligible_target_drives.pop(0)
                pairings.append((hot_plot, selected_hot_plot_target_drive))

                source_drive_transfers_in_flight[hot_plot.source_drive_info.source_drive_config] += 1
                target_host_transfers_in_flight[selected_hot_plot_target_drive.host_config] += 1
                target_drive_transfers_in_flight[(selected_hot_plot_target_drive.host_config, selected_hot_plot_target_drive.target_drive_info.target_drive_config)] += 1
                target_drive_committed_bytes[(selected_hot_plot_target_drive.host_config, selected_hot_plot_target_drive.target_drive_info.target_drive_config)] += hot_plot.source_plot.size
                if not selected_hot_plot_target_drive.is_local():
                    remote_transfers += 1

            elif frequency_capped_hot_plot_target_drives:
                # in that case that at least one target drive was not selected because of capping,
                # we consider this plot to have only failed due to capping rules.
                unpaired_hot_plots_due_to_capping.append(hot_plot)

            else:
                # if we've hit this case, the plot was not paired because there was no drive which could fit it
                unpaired_hot_plots_due_to_no_space.append(hot_plot)

        return GetSourceTargetPairingsResult(pairings, unpaired_hot_plots_due_to_capping, unpaired_hot_plots_due_to_no_space)
