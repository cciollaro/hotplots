from dataclasses import dataclass
import os
from typing import List, Union
from hotplots.hotplots_config import SourceConfig, TargetDriveConfig, RemoteTargetsConfig, LocalHostConfig, \
    SourceDriveConfig, RemoteHostConfig


@dataclass
class PlotNameMetadata:
    k: int
    year: int
    month: int
    day: int
    hour: int
    minute: int
    plot_id: str

    @staticmethod
    def parse_from_filename(plot_filename):
        """
        Parses the metadata out of a plot file name - works for complete
        plots as well as temporary rsync plots (starting with . and ends with .xxxxxx random characters)
        """
        basename = os.path.basename(plot_filename)
        if basename.startswith("."):
            # .plot-k32-2021-05-24-12-36-990e8afe5494e4fd91aef0bcd5548f529895400011528e56094c1c3c96edcd27.plot.y29pgW
            _, filename, _, _ = basename.split('.')
        else:
            # plot-k32-2021-05-24-12-36-990e8afe5494e4fd91aef0bcd5548f529895400011528e56094c1c3c96edcd27.plot
            filename, _ = basename.split('.')

        # plot-k32-2021-05-24-12-36-990e8afe5494e4fd91aef0bcd5548f529895400011528e56094c1c3c96edcd27
        _, k_str, year, month, day, hour, minute, plot_id = filename.split('-')

        return PlotNameMetadata(
            int(k_str.strip("k")),
            year,
            month,
            day,
            hour,
            minute,
            plot_id
        )



@dataclass
class InFlightTransfer:
    filename: str
    current_file_size: int
    plot_name_metadata: PlotNameMetadata


@dataclass
class TargetDriveInfo:
    target_drive_config: TargetDriveConfig
    total_bytes: int
    free_bytes: int
    in_flight_transfers: List[InFlightTransfer]

@dataclass
class LocalTargetsInfo:
    local_host_config: LocalHostConfig
    target_drive_infos: list[TargetDriveInfo]

@dataclass
class SourcePlot:
    absolute_reference: str
    basename: str
    size: int
    plot_name_metadata: PlotNameMetadata

@dataclass
class SourceDriveInfo:
    source_drive_config: SourceDriveConfig
    total_bytes: int
    free_bytes: int
    source_plots: List[SourcePlot]

@dataclass
class SourceInfo:
    source_config: SourceConfig
    source_drive_infos: List[SourceDriveInfo]


@dataclass
class RemoteHostInfo:
    remote_host_config: RemoteHostConfig
    target_drive_infos: list[TargetDriveInfo]


@dataclass
class RemoteTargetsInfo:
    remote_target_config: RemoteTargetsConfig
    remote_host_infos: list[RemoteHostInfo]


@dataclass
class HotPlot:
    source_drive_info: SourceDriveInfo
    source_plot: SourcePlot


@dataclass
class HotPlotTargetDrive:
    host_config: Union[LocalHostConfig, RemoteHostConfig]
    target_drive_info: TargetDriveInfo
