import logging

from hotplots.hotplots_config import HotplotsConfig
from hotplots.hotplots_io import HotplotsIO
from hotplots.hotplots_pairing_engine import EligiblePairingsResult
from hotplots.hotplots_pairing_engine import HotplotsPairingEngine, PlotReplacementResult
from hotplots.models import SourceInfo, TargetsInfo


class Hotplots:
    def __init__(self, config: HotplotsConfig, hotplots_io: HotplotsIO):
        self.config = config
        self.hotplots_io = hotplots_io

    def run(self):
        # First check all sources to see if there are any plots at all
        source_info: SourceInfo = self.hotplots_io.get_source_info(self.config.source)

        # If no plot files, there's definitely nothing to do
        if all([not s.source_plots for s in source_info.source_drive_infos]):
            logging.info("didn't find any source plot files")
            return

        # Next, let's fetch disk space and staged plots information from all targets
        # These are fairly light operations, and provides all the info we need to know
        # to determine if pairings can be made.
        targets_info: TargetsInfo = TargetsInfo(
            self.config.targets,
            self.hotplots_io.get_local_target_info(self.config.targets.local),
            self.hotplots_io.get_remote_targets_info(self.config.targets.remote)
        )

        pairings_result = HotplotsPairingEngine.get_pairings_result(source_info, targets_info)

        if isinstance(pairings_result, PlotReplacementResult):
            # not an eligible pairing, but we can try to replace plots
            # if successful, will update pairings_request with an eligible pairing
            logging.info("Let's try plot replacement for local drives")
            pairings_result = HotplotsPairingEngine.get_pairings_result_with_replacement(pairings_result)

        if isinstance(pairings_result, EligiblePairingsResult):
            [
                self.hotplots_io.transfer_plot(hot_plot, hot_plot_target_drive)
                for (hot_plot, hot_plot_target_drive)
                in pairings_result.pairings
            ]
        else:
            # no action, we could arrive here by a capping ineligility or a failed replacement
            logging.info("No action available to take at this time.")
            return


