import logging
import os
import socket
from glob import glob

import paramiko

from hotplots.models import PlotNameMetadata, InFlightTransfer, SourceDriveInfo, RemoteHostInfo
from hotplots.models import SourceConfig, SourcePlot, SourceInfo, LocalTargetConfig, LocalTargetInfo, RemoteTargetsConfig, \
    RemoteTargetsInfo, TargetDriveInfo


class FSAccess:
    """
    The goal here is to encapsulate all of the FS access, so things can more easily be tested and mocked.
    """

    @staticmethod
    def get_source_info(source_config: SourceConfig) -> SourceInfo:
        logging.info("getting source info %s" % source_config)
        source_drive_infos = []
        for source_drive_config in source_config.drives:
            # find all the plots in the drive
            source_plots = []
            for source_plot_absolute_reference in glob(os.path.join(source_drive_config.path, "*.plot")):
                source_plot = SourcePlot(
                    source_plot_absolute_reference,
                    os.path.basename(source_plot_absolute_reference),
                    os.path.getsize(source_plot_absolute_reference),
                    PlotNameMetadata.parse_from_filename(source_plot_absolute_reference)
                )

                source_plots.append(source_plot)

            # find out how much space is available on the drive
            free_1k_blocks_cmd = "df %s | tail -n 1 | awk '{print $4}'" % source_drive_config.path
            free_bytes = int(os.popen(free_1k_blocks_cmd).read().rstrip()) * 1000

            source_drive_info = SourceDriveInfo(
                source_drive_config,
                free_bytes,
                source_plots
            )
            source_drive_infos.append(source_drive_info)

        return SourceInfo(
            source_config,
            source_drive_infos
        )


    @staticmethod
    def get_local_target_info(local_target_config: LocalTargetConfig) -> LocalTargetInfo:
        logging.info("getting local target info for %s" % local_target_config)

        target_disk_infos = []
        for target_drive_config in local_target_config.drives:
            free_1k_blocks_cmd = "df %s | tail -n 1 | awk '{print $4}'" % target_drive_config.path
            in_flight_transfers_cmd = "find %s -name '.*.plot.*'" % target_drive_config.path

            free_bytes = int(os.popen(free_1k_blocks_cmd).read().rstrip()) * 1000
            in_flight_transfers_str = os.popen(in_flight_transfers_cmd).read().rstrip()
            if len(in_flight_transfers_str) == 0:
                in_flight_transfer_filenames = []
            else:
                in_flight_transfer_filenames = in_flight_transfers_str.split("\n")

            in_flight_transfers = []
            for in_flight_transfer_filename in in_flight_transfer_filenames:
                in_flight_transfer_absolute_reference = os.path.join(target_drive_config.path, in_flight_transfer_filename)
                file_size_cmd = "stat -c%s " + in_flight_transfer_absolute_reference
                current_file_size = int(os.popen(file_size_cmd).read().rstrip())
                in_flight_transfer = InFlightTransfer(in_flight_transfer_filename, current_file_size)
                in_flight_transfers.append(in_flight_transfer)

            target_disk_info = TargetDriveInfo(
                target_drive_config,
                free_bytes,
                in_flight_transfers
            )

            target_disk_infos.append(target_disk_info)

        local_target_info = LocalTargetInfo(
            local_target_config,
            target_disk_infos
        )
        logging.info("got local target info %s" % local_target_info)

        return local_target_info


    @staticmethod
    def get_remote_target_info(remote_targets_config: RemoteTargetsConfig) -> RemoteTargetsInfo:

        remote_host_infos = []
        for remote_host_config in remote_targets_config.hosts:
            logging.info("getting remote info for %s" % remote_host_config)

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            resolved_ip = socket.gethostbyname(remote_host_config.hostname)
            client.connect(resolved_ip, port=remote_host_config.port, username=remote_host_config.username)

            target_drive_infos = []
            for target_drive_config in remote_host_config.drives:
                free_1k_blocks_cmd = "df %s | tail -n 1 | awk '{print $4}'" % target_drive_config.path
                in_flight_transfers_cmd = "find %s -name '.*.plot.*'" % target_drive_config.path

                _, free_1k_blocks_stdout, _ = client.exec_command(free_1k_blocks_cmd)
                free_bytes = int(free_1k_blocks_stdout.read().decode("utf-8").rstrip()) * 1000

                _, in_flight_transfers_stdout, _ = client.exec_command(in_flight_transfers_cmd)
                in_flight_transfers_str = in_flight_transfers_stdout.read().decode("utf-8").rstrip()
                if len(in_flight_transfers_str) == 0:
                    in_flight_transfer_filenames = []
                else:
                    in_flight_transfer_filenames = in_flight_transfers_str.split("\n")

                in_flight_transfers = []
                for in_flight_transfer_filename in in_flight_transfer_filenames:
                    in_flight_transfer_absolute_reference = os.path.join(target_drive_config.path, in_flight_transfer_filename)
                    file_size_cmd = "stat -c%s " + in_flight_transfer_absolute_reference
                    _, current_file_size_stdout, _ = client.exec_command(file_size_cmd)
                    current_file_size = int(current_file_size_stdout.read().decode("utf-8").rstrip())
                    in_flight_transfer = InFlightTransfer(in_flight_transfer_filename, current_file_size)
                    in_flight_transfers.append(in_flight_transfer)

                target_drive_info = TargetDriveInfo(
                    target_drive_config,
                    free_bytes,
                    in_flight_transfers
                )
                target_drive_infos.append(target_drive_info)

            client.close()

            remote_host_info = RemoteHostInfo(
                remote_host_config,
                target_drive_infos
            )
            logging.info("got remote host info %s" % remote_host_info)
            remote_host_infos.append(remote_host_info)

        return RemoteTargetsInfo(
            remote_targets_config,
            remote_host_infos
        )
