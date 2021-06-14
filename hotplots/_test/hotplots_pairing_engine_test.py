import unittest

from hotplots._test.helpers.test_helpers import TestHelpers
from hotplots.constants import Constants
from hotplots.hotplots_config import SourceDriveConfig, SourceConfig, RemoteTargetsConfig, RemoteHostConfig, \
    TargetDriveConfig, LocalHostConfig, TargetsConfig
from hotplots.hotplots_pairing_engine import HotplotsPairingEngine, EligiblePairingsResult
from hotplots.models import SourceInfo, SourceDriveInfo, HotPlot, RemoteTargetsInfo, RemoteHostInfo, TargetDriveInfo, \
    TargetsInfo, LocalTargetsInfo, HotPlotTargetDrive


class HotplotsPairingEngineTest(unittest.TestCase):
    def test__source__plot_with_oldest_timestamp(self):
        # Source configuration and info
        source_drive_1_config = SourceDriveConfig("/mnt/source1", 1)
        source_drive_1_source_plot_1 = TestHelpers.create_mock_source_plot(source_drive_1_config, 32, 2021, 6, 27, 21, 59)
        source_drive_1_info = SourceDriveInfo(source_drive_1_config, 1 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_drive_1_source_plot_1])

        source_drive_2_config = SourceDriveConfig("/mnt/source2", 1)
        source_drive_2_source_plot_1 = TestHelpers.create_mock_source_plot(source_drive_2_config, 32, 2021, 6, 27, 21, 58)
        source_drive_2_info = SourceDriveInfo(source_drive_2_config, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_drive_2_source_plot_1])

        source_config = SourceConfig([source_drive_1_config, source_drive_2_config], 60, "plot_with_oldest_timestamp")
        source_info = SourceInfo(source_config, [source_drive_1_info, source_drive_2_info])

        # Local configuration and info
        local_host_target_drive_1_config = TargetDriveConfig("/mnt/target1", 1)
        local_host_target_drive_1_info = TargetDriveInfo(local_host_target_drive_1_config, 100 * Constants.TERABYTE, 100 * Constants.TERABYTE, [])

        local_host_config = LocalHostConfig([local_host_target_drive_1_config])
        local_targets_info = LocalTargetsInfo(local_host_config, [local_host_target_drive_1_info])

        # Remote configuration and info
        remote_targets_config = RemoteTargetsConfig(1, [])
        remote_targets_info = RemoteTargetsInfo(remote_targets_config, [])

        # Finally
        targets_config = TargetsConfig("config_order", local_host_config, remote_targets_config, "unspecified")
        targets_info = TargetsInfo(targets_config, local_targets_info, remote_targets_info)

        expected = EligiblePairingsResult([
            (HotPlot(source_drive_2_info, source_drive_2_source_plot_1), HotPlotTargetDrive(local_host_config, local_host_target_drive_1_info))
        ])

        self.assertEqual(expected, HotplotsPairingEngine.get_pairings_result(source_info, targets_info))

    def test__source__random(self):
        # Source configuration and info
        source_drive_1_config = SourceDriveConfig("/mnt/source1", 1)
        source_drive_1_source_plot_1 = TestHelpers.create_mock_source_plot(source_drive_1_config, 32, 2021, 6, 27, 21, 59, "a"*64)
        source_drive_1_info = SourceDriveInfo(source_drive_1_config, 1 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_drive_1_source_plot_1])

        source_drive_2_config = SourceDriveConfig("/mnt/source2", 1)
        source_drive_2_source_plot_1 = TestHelpers.create_mock_source_plot(source_drive_2_config, 32, 2021, 6, 27, 21, 59, "b"*64)
        source_drive_2_info = SourceDriveInfo(source_drive_2_config, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_drive_2_source_plot_1])

        source_config = SourceConfig([source_drive_1_config, source_drive_2_config], 60, "random")
        source_info = SourceInfo(source_config, [source_drive_1_info, source_drive_2_info])

        # Local configuration and info
        local_host_target_drive_1_config = TargetDriveConfig("/mnt/target1", 1)
        local_host_target_drive_1_info = TargetDriveInfo(local_host_target_drive_1_config, 100 * Constants.TERABYTE, 100 * Constants.TERABYTE, [])

        local_host_config = LocalHostConfig([local_host_target_drive_1_config])
        local_targets_info = LocalTargetsInfo(local_host_config, [local_host_target_drive_1_info])

        # Remote configuration and info
        remote_targets_config = RemoteTargetsConfig(1, [])
        remote_targets_info = RemoteTargetsInfo(remote_targets_config, [])

        # Finally
        targets_config = TargetsConfig("config_order", local_host_config, remote_targets_config, "unspecified")
        targets_info = TargetsInfo(targets_config, local_targets_info, remote_targets_info)

        expected = EligiblePairingsResult([
            (HotPlot(source_drive_1_info, source_drive_1_source_plot_1), HotPlotTargetDrive(local_host_config, local_host_target_drive_1_info))
        ])

        self.assertEqual(expected, HotplotsPairingEngine.get_pairings_result(source_info, targets_info))

    def test_two_eligible_targets(self):
        # Source configuration and info
        source_drive_1_config = SourceDriveConfig("/mnt/source1", 1)
        source_drive_1_source_plot_1 = TestHelpers.create_mock_source_plot(source_drive_1_config, 32, 2021, 6, 27, 21, 59)
        source_drive_1_info = SourceDriveInfo(source_drive_1_config, 1 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_drive_1_source_plot_1])

        source_drive_2_config = SourceDriveConfig("/mnt/source2", 1)
        source_drive_2_source_plot_1 = TestHelpers.create_mock_source_plot(source_drive_2_config, 32, 2021, 6, 27, 21, 58)
        source_drive_2_info = SourceDriveInfo(source_drive_2_config, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_drive_2_source_plot_1])

        source_config = SourceConfig([source_drive_1_config, source_drive_2_config], 60, "plot_with_oldest_timestamp")
        source_info = SourceInfo(source_config, [source_drive_1_info, source_drive_2_info])

        # Local configuration and info
        local_host_target_drive_1_config = TargetDriveConfig("/mnt/target1", 1)
        local_host_target_drive_1_info = TargetDriveInfo(local_host_target_drive_1_config, 100 * Constants.TERABYTE, 100 * Constants.TERABYTE, [])

        local_host_config = LocalHostConfig([local_host_target_drive_1_config])
        local_targets_info = LocalTargetsInfo(local_host_config, [local_host_target_drive_1_info])

        # Remote configuration and info
        remote_host_1_target_drive_1_config = TargetDriveConfig("/mnt/target1", 1)
        remote_host_1_target_drive_1_info = TargetDriveInfo(remote_host_1_target_drive_1_config, 100*Constants.TERABYTE, 100*Constants.TERABYTE, [])

        remote_host_1_config = RemoteHostConfig("host1", "user1", 22, 1, [remote_host_1_target_drive_1_config])
        remote_host_1_info = RemoteHostInfo(remote_host_1_config, [remote_host_1_target_drive_1_info])

        remote_targets_config = RemoteTargetsConfig(1, [remote_host_1_config])
        remote_targets_info = RemoteTargetsInfo(remote_targets_config, [remote_host_1_info])

        # Finally
        targets_config = TargetsConfig("config_order", local_host_config, remote_targets_config, "local")
        targets_info = TargetsInfo(targets_config, local_targets_info, remote_targets_info)

        expected = EligiblePairingsResult([
            (HotPlot(source_drive_2_info, source_drive_2_source_plot_1), HotPlotTargetDrive(local_host_config, local_host_target_drive_1_info)),
            (HotPlot(source_drive_1_info, source_drive_1_source_plot_1), HotPlotTargetDrive(remote_host_1_config, remote_host_1_target_drive_1_info)),
        ])

        actual = HotplotsPairingEngine.get_pairings_result(source_info, targets_info)
        self.assertEqual(2, len(actual.pairings))
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
