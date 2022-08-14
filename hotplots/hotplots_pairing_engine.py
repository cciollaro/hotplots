from dataclasses import dataclass
from typing import List, Tuple
from collections import defaultdict

from hotplots.models import SourceInfo, TargetsInfo, HotPlot, HotPlotTargetDrive
from hotplots.pairing_state import PairingState
from hotplots.hotplots_io import HotplotsIO


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
    unpaired_hot_plots: List[HotPlot]
    filled_target_drives: List[HotPlotTargetDrive]


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
            return PlotReplacementResult(pairing_state.get_unpaired_hot_plots_due_to_lack_of_space(), filled_hot_plot_target_drives)

    @staticmethod
    def get_pairings_result_with_replacement(plot_replacement_result):
        # we have already identified the unpaired hotplots, let's try to create some space
        # for a given target based on their replacement policies
        unpaired_hotplots = plot_replacement_result.unpaired_hot_plots
        targets = plot_replacement_result.filled_target_drives

        all_deleteable_files = []
        pairings = []
        capping_limits = defaultdict(int)

        for target in targets:
            config = target.target_drive_info.target_drive_config
            plot_replacement = config.plot_replacement
            if plot_replacement.enabled:
                target_path = config.path
                strategy = plot_replacement.type
                value = plot_replacement.value

                capping_limits[target_path] = config.max_concurrent_inbound_transfers

                if strategy == "from-directory":
                    # confirm that we have the same base dir (doesn't necessarily mean we're on the
                    # same drive for a bad config, but it helps foot-shooting)
                    if not (value.startswith(target_path) or target_path.startswith(value)):
                        print("Bad config for " + target_path + ", from-directory replacement value " + value + " doesn't have same prefix")
                        continue
                    contents = HotplotsIO.get_files_with_sizes_in_dir(value)
                    sorted_contents = sorted(contents, reverse=True)
                    # hardcoded, we will only delete files ending in .plot
                    # TODO: treat deleteable files as real plot references?
                    # buuut we do also want to handle junk/incomplete plot deletion too probably
                    deleteable_files = list(map(lambda x: (x[0], x[1], target_path, target), filter(lambda x: x[1].endswith(".plot"), sorted_contents)))
                    
                    # now our list is sorted by largest file sizes, and only files that end in *.plot, we can mark to delete with great prejudice

                    if len(deleteable_files) > 0:
                        all_deleteable_files += deleteable_files
                
                # TODO: other strategies, time-before, public-key, legacy-plot

        # a mixed drive-list of all deleteable files, sorted by filesize
        coldplots = sorted(all_deleteable_files, reverse=True)
        
        # sort our hot plots by their largest filesizes
        hotplots = sorted([
            (hotplot.source_plot.size, hotplot.source_plot.absolute_reference, hotplot)
            for hotplot
            in unpaired_hotplots
        ], reverse=True)

        capping_counts = defaultdict(int)
        # Question: do we need to check in-flight transfers here? Or will that be handled automatically from the previous pairing call
        
        # A greedy algorithm that will just try to pair up the biggest hot plots
        # with the biggest "cold" plots. If the capping for the current cold plot's drive
        # is met, or the hot plot doesn't fit, will move onto the next cold/hot plot
        cur_hotplot_idx = 0
        cur_coldplot_idx = 0

        while cur_hotplot_idx < len(hotplots) and cur_coldplot_idx < len(coldplots):
            cur_hotplot = hotplots[cur_hotplot_idx]
            cur_coldplot = coldplots[cur_coldplot_idx]

            # unpack hot and cold tuples from the sorting
            hot_size, hot_path, hot_plot_ref = cur_hotplot
            cold_size, cold_path, target_path, target_drive = cur_coldplot

            # if this drive is already maxed out with capping rules, skip to
            # the next coldplot
            if capping_counts[target_path] >= capping_limits[target_path]:
                cur_coldplot_idx += 1
                continue

            # the excess bytes on the target drive
            free_bytes = target_drive.target_drive_info.free_bytes

            if hot_size > cold_size + free_bytes:
                # hot plot too big to fit if we remove the cold plot,
                # even given the free_bytes, move on
                # TODO: mark as unprocesed_due_to_too_big for later
                cur_hotplot_idx += 1
                continue

            # deleting the cold plot here will make room for our hot plot!
            # print("Would've deleted ", cold_path)
            # print("Committing pairing: ", (hot_path, target_path))
            # print("")
            HotplotsIO.delete_file(cold_path, True)
            pairings.append((hot_plot_ref, target_drive))
        
            cur_hotplot_idx += 1
            cur_coldplot_idx += 1

            capping_counts[target_path] += 1

        if len(pairings) > 0:
            return EligiblePairingsResult(pairings)
        return NoActionResult
