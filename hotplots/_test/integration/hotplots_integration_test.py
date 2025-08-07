import unittest
import tempfile
import os
import yaml
from pathlib import Path

from hotplots.hotplots import Hotplots
from hotplots.hotplots_io import HotplotsIO

class HotplotsIntegrationTest(unittest.TestCase):
    def test_simple_move(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup temporary directories
            source_path = Path(temp_dir) / "source"
            target_path = Path(temp_dir) / "target"
            os.makedirs(source_path)
            os.makedirs(target_path)

            # Create a dummy plot file
            plot_filename = "plot-k32-2021-06-01-00-00.plot"
            with open(source_path / plot_filename, "w") as f:
                f.write("dummy plot data")

            # Create a temporary config file
            config_path = Path(temp_dir) / "config.yaml"
            config = {
                "logging": {
                    "level": "DEBUG",
                    "stdout": {"enabled": True},
                    "file": {"enabled": False},
                },
                "source": {
                    "check_source_drives_sleep_seconds": 1,
                    "selection_strategy": "plot_with_oldest_timestamp",
                    "drives": [{"path": str(source_path), "max_concurrent_outbound_transfers": 1}],
                },
                "targets": {
                    "target_host_preference": "local",
                    "selection_strategy": "drive_with_most_space_remaining",
                    "local": {
                        "drives": [
                            {
                                "path": str(target_path),
                                "max_concurrent_inbound_transfers": 1,
                            }
                        ]
                    },
                    "remote": {"max_concurrent_outbound_transfers": 1, "hosts": []},
                },
            }
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            # Run hotplots
            hotplots_io = HotplotsIO()
            loaded_config = hotplots_io.load_config_file(str(config_path))
            hotplots = Hotplots(loaded_config, hotplots_io)
            hotplots.run()

            # Assertions
            self.assertFalse(os.path.exists(source_path / plot_filename))
            self.assertTrue(os.path.exists(target_path / plot_filename))

if __name__ == '__main__':
    unittest.main()
