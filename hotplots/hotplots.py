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
from hotplots.models import SourceInfo, LocalTargetsInfo, RemoteTargetsInfo, TargetsInfo


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

        # Next, let's fetch disk space and staged plots information from all targets
        # These are fairly light operations, and provides all the info we need to know if we can
        # perform a simple transfer.
        targets_info: TargetsInfo = TargetsInfo(
            FSAccess.get_local_target_info(self.config.targets.local),
            FSAccess.get_remote_targets_info(self.config.targets.remote)
        )

        # possible results:
        # - no action
        # - transfers
        # - plot replacement
        actions_result = HotplotsEngine.get_actions(self.config, source_info, targets_info)




        # FSAccess.process_actions(actions)
