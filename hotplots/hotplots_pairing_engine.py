from hotplots.models import SourceInfo, TargetsInfo, GetActionsNoActionResult, GetActionsTransfersResult, \
    GetActionsPlotReplacementResult


from hotplots.pairing_state import PairingState


class HotplotsPairingEngine:
    # for simplicity, either all actions are going to be movements, or all actions are going to be plot_replacement.
    # that means to start plot_replacement we're going to wait until we have a run where all drives are
    # full (or committed to be full) for all potential hot plots.
    @staticmethod
    def get_actions(source_info: SourceInfo, targets_info: TargetsInfo):
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
            # In the case that pairings were made, we're simply going to execute them and defer other things
            # such as plot replacement to the next invocation.
            return GetActionsTransfersResult(pairing_state.get_pairings())

        elif pairing_state.get_unpaired_hot_plots_due_to_capping():
            # If any of our hot plots weren't transferrable because of capping, we'll simply recommend no action
            return GetActionsNoActionResult()

        elif pairing_state.get_unpaired_hot_plots_due_to_lack_of_space():
            # In the case that all of our hotplots had nowhere to go, we can recommend plot_replacement for all hot_plots
            return GetActionsPlotReplacementResult()
