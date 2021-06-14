import random
from collections import defaultdict
from typing import Tuple, Union, List

from hotplots.constants import Constants
from hotplots.hotplots_config import SourceDriveConfig, LocalHostConfig, RemoteHostConfig, TargetDriveConfig
from hotplots.models import SourceInfo, TargetsInfo, HotPlot, HotPlotTargetDrive


class PairingState:
    __source_info: SourceInfo = None
    __targets_info: TargetsInfo = None

    __initially_skipped_hot_plots: List[HotPlot] = []
    __unprocessed_hot_plots: List[HotPlot] = []

    __pairings: List[Tuple[HotPlot, HotPlotTargetDrive]] = []
    __unpaired_hot_plots_due_to_capping: List[HotPlot] = []
    __unpaired_hot_plots_due_to_lack_of_space: List[HotPlot] = []

    __all_hot_plot_target_drives: List[HotPlotTargetDrive] = []

    __source_drive_bytes_in_flight: dict[SourceDriveConfig, int] = defaultdict(lambda: 0)
    __source_drive_transfers_in_flight: dict[SourceDriveConfig, int] = defaultdict(lambda: 0)

    __target_host_transfers_in_flight: dict[Union[LocalHostConfig, RemoteHostConfig], int] = defaultdict(lambda: 0)

    __target_drive_bytes_in_flight: dict[Tuple[Union[LocalHostConfig, RemoteHostConfig], TargetDriveConfig], int] = defaultdict(lambda: 0)
    __target_drive_transfers_in_flight: dict[Tuple[Union[LocalHostConfig, RemoteHostConfig], TargetDriveConfig], int] = defaultdict(lambda: 0)

    __total_remote_transfers_from_source_host: int = 0

    __source_drive_config_order_lookup: dict[SourceDriveConfig, int] = {}
    __target_drive_config_order_lookup: dict[TargetDriveConfig, int] = {}

    def __init__(self, source_drive_info: SourceInfo, targets_info: TargetsInfo):
        self.__source_info = source_drive_info
        self.__targets_info = targets_info

        self.__initialize_config_order_lookups()

        initial_transfers_map: dict[str, Tuple[Union[LocalHostConfig, RemoteHostConfig], TargetDriveConfig]] = {}

        # update state w/ local target info
        target_host_config = self.__targets_info.local_targets_info.local_host_config
        for target_drive_info in self.__targets_info.local_targets_info.target_drive_infos:
            for in_flight_transfer in target_drive_info.in_flight_transfers:
                initial_transfers_map[in_flight_transfer.plot_name_metadata.plot_id] = (self.__targets_info.local_targets_info.local_host_config, target_drive_info.target_drive_config)
                self.__target_host_transfers_in_flight[target_host_config] += 1
                target_host_and_drive_configs = (target_host_config, target_drive_info.target_drive_config)
                self.__target_drive_bytes_in_flight[target_host_and_drive_configs] += (Constants.PLOT_BYTES_BY_K[in_flight_transfer.plot_name_metadata.k] - in_flight_transfer.current_file_size)

            hot_plot_target_drive = HotPlotTargetDrive(
                target_host_config,
                target_drive_info
            )
            self.__all_hot_plot_target_drives.append(hot_plot_target_drive)

        # update state w/ remote target info
        for remote_host_info in self.__targets_info.remote_targets_info.remote_host_infos:
            target_host_config = remote_host_info.remote_host_config
            for target_drive_info in remote_host_info.target_drive_infos:
                for in_flight_transfer in target_drive_info.in_flight_transfers:
                    initial_transfers_map[in_flight_transfer.plot_name_metadata.plot_id] = (remote_host_info.remote_host_config, target_drive_info.target_drive_config)
                    self.__target_host_transfers_in_flight[target_host_config] += 1
                    target_host_and_drive_configs = (target_host_config, target_drive_info.target_drive_config)
                    self.__target_drive_bytes_in_flight[target_host_and_drive_configs] += (Constants.PLOT_BYTES_BY_K[in_flight_transfer.plot_name_metadata.k] - in_flight_transfer.current_file_size)

                hot_plot_target_drive = HotPlotTargetDrive(
                    remote_host_info.remote_host_config,
                    target_drive_info
                )
                self.__all_hot_plot_target_drives.append(hot_plot_target_drive)

        # update state w/ source drive info
        for source_drive_info in self.__source_info.source_drive_infos:
            for source_plot in source_drive_info.source_plots:
                if source_plot.plot_name_metadata().plot_id in initial_transfers_map:
                    (host_config, target_drive_config) = initial_transfers_map[source_plot.plot_name_metadata().plot_id]
                    if not host_config.is_local():
                        self.__total_remote_transfers_from_source_host += 1

                    self.__source_drive_transfers_in_flight[source_drive_info.source_drive_config] += 1
                    self.__source_drive_bytes_in_flight[source_drive_info.source_drive_config] += source_plot.size
                    self.__initially_skipped_hot_plots.append(HotPlot(source_drive_info, source_plot))
                else:
                    self.__unprocessed_hot_plots.append(HotPlot(source_drive_info, source_plot))

    def commit_pairing(self, hot_plot: HotPlot, hot_plot_target_drive: HotPlotTargetDrive):
        self.__pairings.append((hot_plot, hot_plot_target_drive))

        if not hot_plot_target_drive.is_local():
            self.__total_remote_transfers_from_source_host += 1

        source_drive_config = hot_plot.source_drive_info.source_drive_config
        self.__source_drive_transfers_in_flight[source_drive_config] += 1
        self.__source_drive_bytes_in_flight[source_drive_config] += hot_plot.source_plot.size

        target_host_config = hot_plot_target_drive.host_config
        self.__target_host_transfers_in_flight[target_host_config] += 1

        target_drive_id = (target_host_config, hot_plot_target_drive.target_drive_info.target_drive_config)
        self.__target_drive_transfers_in_flight[target_drive_id] += 1
        self.__target_drive_bytes_in_flight[target_drive_id] += hot_plot.source_plot.size

    def get_pairings(self):
        return self.__pairings

    def get_unpaired_hot_plots_due_to_capping(self):
        return self.__unpaired_hot_plots_due_to_capping

    def get_unpaired_hot_plots_due_to_lack_of_space(self):
        return self.__unpaired_hot_plots_due_to_lack_of_space

    def commit_unpaired_due_to_capping(self, hot_plot: HotPlot):
        self.__unpaired_hot_plots_due_to_capping.append(hot_plot)

    def commit_unpaired_due_to_lack_of_space(self, hot_plot: HotPlot):
        self.__unpaired_hot_plots_due_to_lack_of_space.append(hot_plot)

    def get_unprocessed_hot_plots_size(self):
        return len(self.__unprocessed_hot_plots)

    def pop_next_unprocessed_hot_plot(self):
        self.__unprocessed_hot_plots = self.rank_hot_plots(self.__unprocessed_hot_plots)
        return self.__unprocessed_hot_plots.pop(0)

    def get_all_hot_plot_target_drives(self) -> List[HotPlotTargetDrive]:
        return self.__all_hot_plot_target_drives

    def rank_hot_plots(self, hot_plots: List[HotPlot]) -> List[HotPlot]:
        selection_strategy = self.__source_info.source_config.selection_strategy
        if selection_strategy == "plot_with_oldest_timestamp":
            def key_func(hot_plot: HotPlot):
                m = hot_plot.source_plot.plot_name_metadata()
                return m.year, m.month, m.day, m.hour, m.minute

            return sorted(hot_plots, key=key_func)
        elif selection_strategy == "drive_with_least_space_remaining":
            def key_func(hot_plot: HotPlot):
                bytes_in_flight = self.__source_drive_bytes_in_flight[hot_plot.source_drive_info.source_drive_config]
                return hot_plot.source_drive_info.free_bytes + bytes_in_flight

            return sorted(hot_plots, key=key_func)
        elif selection_strategy == "drive_with_lowest_percent_space_remaining":
            def key_func(hot_plot: HotPlot):
                bytes_in_flight = self.__source_drive_bytes_in_flight[hot_plot.source_drive_info.source_drive_config]
                return hot_plot.source_drive_info.total_bytes / (hot_plot.source_drive_info.free_bytes + bytes_in_flight)

            return sorted(hot_plots, key=key_func)
        elif selection_strategy == "config_order":
            def key_func(hot_plot: HotPlot):
                return self.__source_drive_config_order_lookup[hot_plot.source_drive_info.source_drive_config]

            return sorted(hot_plots, key=key_func)
        elif selection_strategy == "random":
            def key_func(hot_plot: HotPlot):
                # for random, we'll just sort by the plot_id which is randomly generated under normal circumstances
                return hot_plot.source_plot.plot_name_metadata().plot_id

            return sorted(hot_plots, key=key_func)

    def rank_eligible_hot_plot_target_drives(self, eligible_hot_plot_target_drives: List[HotPlotTargetDrive]) -> List[HotPlotTargetDrive]:
        def naive_rank_hot_plot_target_drives():
            selection_strategy = self.__targets_info.targets_config.selection_strategy
            if selection_strategy == "config_order":
                def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                    return self.__target_drive_config_order_lookup[hot_plot_target_drive.target_drive_info.target_drive_config]
                return sorted(eligible_hot_plot_target_drives, key=key_func)
            elif selection_strategy == "drive_with_least_space_remaining":
                def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                    return hot_plot_target_drive.target_drive_info.free_bytes - self.__target_drive_bytes_in_flight[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                return sorted(eligible_hot_plot_target_drives, key=key_func)
            elif selection_strategy == "drive_with_most_space_remaining":
                def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                    return hot_plot_target_drive.target_drive_info.free_bytes - self.__target_drive_bytes_in_flight[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                return sorted(eligible_hot_plot_target_drives, key=key_func, reverse=True)
            elif selection_strategy == "drive_with_lowest_percent_space_remaining":
                def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                    uncommitted_bytes = hot_plot_target_drive.target_drive_info.free_bytes - self.__target_drive_bytes_in_flight[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                    return uncommitted_bytes / hot_plot_target_drive.target_drive_info.total_bytes
                return sorted(eligible_hot_plot_target_drives, key=key_func)
            elif selection_strategy == "drive_with_highest_percent_space_remaining":
                def key_func(hot_plot_target_drive: HotPlotTargetDrive):
                    uncommitted_bytes = hot_plot_target_drive.target_drive_info.free_bytes - self.__target_drive_bytes_in_flight[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)]
                    return uncommitted_bytes / hot_plot_target_drive.target_drive_info.total_bytes
                return sorted(eligible_hot_plot_target_drives, key=key_func, reverse=True)
            elif selection_strategy == "random":
                # TODO: any way to do this pseudo-randomly based on state for repeatable tests?
                return sorted(eligible_hot_plot_target_drives, key=lambda x: random.random())

        naive_ranked_hot_plot_target_drives = naive_rank_hot_plot_target_drives()

        if self.__targets_info.targets_config.target_host_preference == "unspecified":
            return naive_ranked_hot_plot_target_drives

        # partition by local or remote, maintaining naive ranking
        ranked_local_hot_plot_target_drives = [x for x in naive_ranked_hot_plot_target_drives if x.is_local()]
        ranked_remote_hot_plot_target_drives = [x for x in naive_ranked_hot_plot_target_drives if not x.is_local()]

        if self.__targets_info.targets_config.target_host_preference == "local":
            return ranked_local_hot_plot_target_drives + ranked_remote_hot_plot_target_drives
        elif self.__targets_info.targets_config.target_host_preference == "remote":
            return ranked_remote_hot_plot_target_drives + ranked_local_hot_plot_target_drives

    def is_frequency_capped(self, hot_plot: HotPlot, hot_plot_target_drive: HotPlotTargetDrive):
        """
        The ways that can be frequency capped:
          - max concurrent outbound remote transfers
          - source drive max concurrent outbound transfers
          - target drive max concurrent inbound transfers
        """
        max_concurrent_remote_transfers = self.__targets_info.remote_targets_info.remote_target_config.max_concurrent_outbound_transfers
        if self.__total_remote_transfers_from_source_host >= max_concurrent_remote_transfers:
            return True

        source_drive_max_concurrent_outbound_transfers = hot_plot.source_drive_info.source_drive_config.max_concurrent_outbound_transfers
        if self.__source_drive_transfers_in_flight[
            hot_plot.source_drive_info.source_drive_config] >= source_drive_max_concurrent_outbound_transfers:
            return True

        target_drive_max_concurrent_inbound_transfers = hot_plot_target_drive.host_config.max_concurrent_inbound_transfers
        if self.__target_drive_transfers_in_flight[(hot_plot_target_drive.host_config, hot_plot_target_drive.target_drive_info.target_drive_config)] >= target_drive_max_concurrent_inbound_transfers:
            return True

        return False

    def has_enough_space(self, hot_plot: HotPlot, hot_plot_target_drive: HotPlotTargetDrive):
        # Need to check if the target drive has enough space for the hot_plot, while taking into account
        # active transfers (and some fudge factor because our disk space reading and active transfers size reading
        # don't happen at exactly the same time)
        committed_bytes = (self.__target_drive_bytes_in_flight[(hot_plot_target_drive.host_config,
                                                                hot_plot_target_drive.target_drive_info.target_drive_config)] * Constants.STAGED_FILES_ERROR_TERM)
        available_bytes = hot_plot_target_drive.target_drive_info.free_bytes - committed_bytes
        if available_bytes >= hot_plot.source_plot.size:
            return True

        return False

    def __initialize_config_order_lookups(self):
        i = 0
        for source_drive_config in self.__source_info.source_config.drives:
            self.__source_drive_config_order_lookup[source_drive_config] = i
            i += 1

        i = 0
        # Config order is always local then remote since we have no way of knowing which order
        # they appear in the original YAML file.
        # TODO: We could potentially utilize the targets.target_host_preference variable for this.
        for target_drive_config in self.__targets_info.local_targets_info.local_host_config.drives:
            self.__target_drive_config_order_lookup[target_drive_config] = i
            i += 1

        for remote_host in self.__targets_info.remote_targets_info.remote_target_config.hosts:
            for target_drive_config in remote_host.drives:
                self.__target_drive_config_order_lookup[target_drive_config] = i
                i += 1
