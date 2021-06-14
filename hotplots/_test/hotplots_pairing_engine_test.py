import unittest

from hotplots._test.helpers.test_helpers import TestHelpers
from hotplots.constants import Constants
from hotplots.hotplots_config import SourceDriveConfig, SourceConfig
from hotplots.hotplots_pairing_engine import HotplotsPairingEngine
from hotplots.models import SourceInfo, SourceDriveInfo, HotPlot


class HotplotsPairingEngineTest(unittest.TestCase):
    def test_get_ranked_hotplots__no_source_plots(self):
        source_drive_config_1 = SourceDriveConfig("/mnt/source1", 1)
        source_config = SourceConfig([source_drive_config_1], 60, "drive_with_least_space_remaining")

        source_drive_info_1 = SourceDriveInfo(source_drive_config_1, 1 * Constants.TERABYTE, 1 * Constants.TERABYTE, [])
        source_info = SourceInfo(source_config, [source_drive_info_1])

        self.assertEqual(HotplotsPairingEngine.get_ranked_hot_plots(source_info, {}), [])

    def test_get_ranked_hotplots__1_source_plot(self):
        source_drive_config_1 = SourceDriveConfig("/mnt/source1", 1)
        source_config = SourceConfig([source_drive_config_1], 60, "drive_with_least_space_remaining")

        source_plot_1_1 = TestHelpers.create_mock_source_plot(source_drive_config_1, 32, 2021, 6, 27, 21, 59)

        source_drive_info_1 = SourceDriveInfo(source_drive_config_1, 1 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_plot_1_1])
        source_info = SourceInfo(source_config, [source_drive_info_1])

        self.assertEqual(HotplotsPairingEngine.get_ranked_hot_plots(source_info, {}), [HotPlot(source_drive_info_1, source_plot_1_1)])

    def test_get_ranked_hotplots__plot_with_oldest_timestamp(self):
        source_drive_config_1 = SourceDriveConfig("/mnt/source1", 1)
        source_plot_1_1 = TestHelpers.create_mock_source_plot(source_drive_config_1, 32, 2021, 6, 27, 21, 59)

        source_drive_config_2 = SourceDriveConfig("/mnt/source2", 1)
        source_plot_2_1 = TestHelpers.create_mock_source_plot(source_drive_config_2, 32, 2021, 6, 27, 21, 58)

        source_config = SourceConfig([source_drive_config_1, source_drive_config_2], 60, "plot_with_oldest_timestamp")

        source_drive_info_1 = SourceDriveInfo(source_drive_config_1, 1 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_plot_1_1])
        source_drive_info_2 = SourceDriveInfo(source_drive_config_2, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_plot_2_1])
        source_info = SourceInfo(source_config, [source_drive_info_1, source_drive_info_2])

        expected = [
            HotPlot(source_drive_info_2, source_plot_2_1),
            HotPlot(source_drive_info_1, source_plot_1_1)
        ]

        self.assertEqual(HotplotsPairingEngine.get_ranked_hot_plots(source_info, {}), expected)

    def test_get_ranked_hotplots__drive_with_least_space_remaining(self):
        source_drive_config_1 = SourceDriveConfig("/mnt/source1", 1)
        source_plot_1_1 = TestHelpers.create_mock_source_plot(source_drive_config_1, 32, 2021, 6, 27, 21, 59)

        source_drive_config_2 = SourceDriveConfig("/mnt/source2", 1)
        source_plot_2_1 = TestHelpers.create_mock_source_plot(source_drive_config_2, 32, 2021, 6, 27, 21, 58)

        source_config = SourceConfig([source_drive_config_1, source_drive_config_2], 60, "drive_with_least_space_remaining")

        source_drive_info_1 = SourceDriveInfo(source_drive_config_1, 1 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_plot_1_1])
        source_drive_info_2 = SourceDriveInfo(source_drive_config_2, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_plot_2_1])
        source_info = SourceInfo(source_config, [source_drive_info_1, source_drive_info_2])

        expected = [
            HotPlot(source_drive_info_2, source_plot_2_1),
            HotPlot(source_drive_info_1, source_plot_1_1)
        ]

        self.assertEqual(HotplotsPairingEngine.get_ranked_hot_plots(source_info, {}), expected)

    def test_get_ranked_hotplots__drive_with_lowest_percent_space_remaining(self):
        source_drive_config_1 = SourceDriveConfig("/mnt/source1", 1)
        source_plot_1_1 = TestHelpers.create_mock_source_plot(source_drive_config_1, 32, 2021, 6, 27, 21, 59)

        source_drive_config_2 = SourceDriveConfig("/mnt/source2", 1)
        source_plot_2_1 = TestHelpers.create_mock_source_plot(source_drive_config_2, 32, 2021, 6, 27, 21, 58)

        source_config = SourceConfig([source_drive_config_1, source_drive_config_2], 60, "drive_with_lowest_percent_space_remaining")

        source_drive_info_1 = SourceDriveInfo(source_drive_config_1, 10 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_plot_1_1])
        source_drive_info_2 = SourceDriveInfo(source_drive_config_2, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_plot_2_1])
        source_info = SourceInfo(source_config, [source_drive_info_1, source_drive_info_2])

        expected = [
            HotPlot(source_drive_info_1, source_plot_1_1),
            HotPlot(source_drive_info_2, source_plot_2_1)
        ]

        self.assertEqual(HotplotsPairingEngine.get_ranked_hot_plots(source_info, {}), expected)

    def test_get_ranked_hotplots__config_order(self):
        source_drive_config_1 = SourceDriveConfig("/mnt/source1", 1)
        source_plot_1_1 = TestHelpers.create_mock_source_plot(source_drive_config_1, 32, 2021, 6, 27, 21, 59)

        source_drive_config_2 = SourceDriveConfig("/mnt/source2", 1)
        source_plot_2_1 = TestHelpers.create_mock_source_plot(source_drive_config_2, 32, 2021, 6, 27, 21, 58)

        source_config = SourceConfig([source_drive_config_1, source_drive_config_2], 60, "config_order")

        source_drive_info_1 = SourceDriveInfo(source_drive_config_1, 10 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_plot_1_1])
        source_drive_info_2 = SourceDriveInfo(source_drive_config_2, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_plot_2_1])
        source_info = SourceInfo(source_config, [source_drive_info_1, source_drive_info_2])

        expected = [
            HotPlot(source_drive_info_1, source_plot_1_1),
            HotPlot(source_drive_info_2, source_plot_2_1)
        ]

        self.assertEqual(HotplotsPairingEngine.get_ranked_hot_plots(source_info, {}), expected)

    def test_get_ranked_hotplots__random(self):
        source_drive_config_1 = SourceDriveConfig("/mnt/source1", 1)
        source_plot_1_1 = TestHelpers.create_mock_source_plot(source_drive_config_1, 32, 2021, 6, 27, 21, 59, "a"*64)

        source_drive_config_2 = SourceDriveConfig("/mnt/source2", 1)
        source_plot_2_1 = TestHelpers.create_mock_source_plot(source_drive_config_2, 32, 2021, 6, 27, 21, 58, "b"*64)

        source_config = SourceConfig([source_drive_config_1, source_drive_config_2], 60, "random")

        source_drive_info_1 = SourceDriveInfo(source_drive_config_1, 10 * Constants.TERABYTE, 1 * Constants.TERABYTE, [source_plot_1_1])
        source_drive_info_2 = SourceDriveInfo(source_drive_config_2, 1 * Constants.TERABYTE, 600 * Constants.GIGABYTE, [source_plot_2_1])
        source_info = SourceInfo(source_config, [source_drive_info_1, source_drive_info_2])

        expected = [
            HotPlot(source_drive_info_1, source_plot_1_1),
            HotPlot(source_drive_info_2, source_plot_2_1)
        ]

        self.assertEqual(HotplotsPairingEngine.get_ranked_hot_plots(source_info, {}), expected)


if __name__ == '__main__':
    unittest.main()
