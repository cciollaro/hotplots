import unittest
import os
from pathlib import Path

from hotplots._test.integration.integration_test_helpers import HotplotsIntegrationTestBase

class HotplotsIntegrationTest(HotplotsIntegrationTestBase):
    def test_simple_move(self):
        # Create a dummy plot file
        plot_filename = "plot-k32-2021-06-01-00-00.plot"
        self.create_dummy_plot(plot_filename)

        # Create a temporary config file
        config = {
            "logging": {
                "level": "DEBUG",
                "stdout": {"enabled": True},
                "file": {"enabled": False},
            },
            "source": {
                "check_source_drives_sleep_seconds": 1,
                "selection_strategy": "plot_with_oldest_timestamp",
                "drives": [{"path": str(self.source_path), "max_concurrent_outbound_transfers": 1}],
            },
            "targets": {
                "target_host_preference": "local",
                "selection_strategy": "drive_with_most_space_remaining",
                "local": {
                    "drives": [
                        {
                            "path": str(self.target_path),
                            "max_concurrent_inbound_transfers": 1,
                        }
                    ]
                },
                "remote": {"max_concurrent_outbound_transfers": 1, "hosts": []},
            },
        }

        # Run hotplots
        self.run_hotplots(config)

        # Assertions
        self.assertFalse(os.path.exists(self.source_path / plot_filename))
        self.assertTrue(os.path.exists(self.target_path / plot_filename))

    def test_plot_replacement(self):
        # Create a dummy plot file in the source
        new_plot_filename = "plot-k32-2022-01-01-00-00.plot"
        self.create_dummy_plot(new_plot_filename)

        # Create a plot file in the target that can be replaced
        old_plot_filename = "plot-k32-2021-01-01-00-00.plot"
        self.create_dummy_plot_in_target(old_plot_filename)

        # Create a temporary config file
        config = {
            "logging": {
                "level": "DEBUG",
                "stdout": {"enabled": True},
                "file": {"enabled": False},
            },
            "source": {
                "check_source_drives_sleep_seconds": 1,
                "selection_strategy": "plot_with_oldest_timestamp",
                "drives": [{"path": str(self.source_path), "max_concurrent_outbound_transfers": 1}],
            },
            "targets": {
                "target_host_preference": "local",
                "selection_strategy": "drive_with_most_space_remaining",
                "local": {
                    "drives": [
                        {
                            "path": str(self.target_path),
                            "max_concurrent_inbound_transfers": 1,
                            "plot_replacement": {
                                "enabled": True,
                                "type": "timestamp-before",
                                "value": "2021-06-01",
                            }
                        }
                    ]
                },
                "remote": {"max_concurrent_outbound_transfers": 1, "hosts": []},
            },
        }

        # Run hotplots
        self.run_hotplots(config)

        # Assertions
        self.assertFalse(os.path.exists(self.source_path / new_plot_filename))
        self.assertTrue(os.path.exists(self.target_path / new_plot_filename))
        self.assertFalse(os.path.exists(self.target_path / old_plot_filename))

if __name__ == '__main__':
    unittest.main()
