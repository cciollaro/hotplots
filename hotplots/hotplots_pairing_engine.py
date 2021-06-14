from dataclasses import dataclass
from typing import List, Tuple

from hotplots.models import SourceInfo, TargetsInfo, HotPlot, HotPlotTargetDrive
from hotplots.pairing_state import PairingState


class PairingsResult:
    pass


@dataclass
class EligiblePairingsResult(PairingsResult):
    pairings: List[Tuple[HotPlot, HotPlotTargetDrive]]


@dataclass
class NoActionResult(PairingsResult):
    pass


@dataclass
class PlotReplacementResult(PairingsResult):
    pass


class HotplotsPairingEngine:
    @staticmethod
    def get_pairings_result(source_info: SourceInfo, targets_info: TargetsInfo) -> PairingsResult:
        pairing_state = PairingState(source_info, targets_info)

        while pairing_state.get_unprocessed_hot_plots_size() > 0:
            hot_plot = pairing_state.pop_next_unprocessed_hot_plot()

            frequency_capped_hot_plot_target_drives = []
            filled_hot_plot_target_drives = []
            eligible_target_drives = []

            for hot_plot_target_drive in pairing_state.get_all_hot_plot_target_drives():
                if pairing_state.is_frequency_capped(hot_plot, hot_plot_target_drive):
                    frequency_capped_hot_plot_target_drives.append(hot_plot_target_drive)
                elif not pairing_state.has_enough_space(hot_plot, hot_plot_target_drive):
                    filled_hot_plot_target_drives.append(hot_plot_target_drive)
                else:
                    eligible_target_drives.append(hot_plot_target_drive)

            if eligible_target_drives:
                ranked_eligible_target_drives = pairing_state.rank_eligible_hot_plot_target_drives(eligible_target_drives)
                selected_hot_plot_target_drive = ranked_eligible_target_drives.pop(0)
                pairing_state.commit_pairing(hot_plot, selected_hot_plot_target_drive)
            elif frequency_capped_hot_plot_target_drives:
                # in that case that at least one target drive was not selected because of capping,
                # we consider this plot to have only failed due to capping rules.
                pairing_state.commit_unpaired_due_to_capping(hot_plot)
            else:
                # if we've hit this case, the plot was not paired because there was no drive which could fit it
                pairing_state.commit_unpaired_due_to_lack_of_space(hot_plot)

        if pairing_state.get_pairings():
            # In the case that pairings were made, we're simply going to execute them.
            return EligiblePairingsResult(pairing_state.get_pairings())

        elif pairing_state.get_unpaired_hot_plots_due_to_capping():
            # If any of our hot plots weren't transferable because of capping, we'll simply recommend no action
            # Essentially, the capping is considered a temporary state that will clear up if we wait.
            return NoActionResult()

        elif pairing_state.get_unpaired_hot_plots_due_to_lack_of_space():
            # In the case that all hotplots had nowhere to go due to lack of space, we can recommend plot_replacement.
            # Lack of space is not a state that will clear up naturally by waiting.
            return PlotReplacementResult()
