import unittest
import tempfile
import os
import yaml
from pathlib import Path

from hotplots.hotplots import Hotplots
from hotplots.hotplots_io import HotplotsIO

class HotplotsIntegrationTestBase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.source_path = Path(self.temp_dir.name) / "source"
        self.target_path = Path(self.temp_dir.name) / "target"
        os.makedirs(self.source_path)
        os.makedirs(self.target_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_dummy_plot(self, filename, size_gb=1):
        plot_path = self.source_path / filename
        with open(plot_path, "w") as f:
            f.write("dummy plot data")
        # In a real scenario, plot sizes are large. We can simulate this
        # by setting the size of the file without writing all the data.
        # This is not a perfect simulation, but it's good enough for our purposes.
        os.truncate(plot_path, size_gb * 1024 * 1024 * 1024)
        return plot_path

    def create_dummy_plot_in_target(self, filename, size_gb=1):
        plot_path = self.target_path / filename
        with open(plot_path, "w") as f:
            f.write("dummy plot data")
        os.truncate(plot_path, size_gb * 1024 * 1024 * 1024)
        return plot_path

    def run_hotplots(self, config):
        config_path = Path(self.temp_dir.name) / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        hotplots_io = HotplotsIO()
        loaded_config = hotplots_io.load_config_file(str(config_path))
        hotplots = Hotplots(loaded_config, hotplots_io)
        hotplots.run()
