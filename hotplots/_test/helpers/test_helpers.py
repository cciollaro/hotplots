import os

from hotplots.constants import Constants
from hotplots.hotplots_config import SourceDriveConfig
from hotplots.models import SourcePlot
import secrets


class TestHelpers:
    @staticmethod
    def create_mock_source_plot(
            source_drive_config: SourceDriveConfig,
            k: int,
            year: int,
            month: int,
            day: int,
            hour: int,
            minute: int,
            plot_id: str = ""
    ) -> SourcePlot:
        if not plot_id:
            plot_id = secrets.token_hex(64)

        plot_filename = "plot-k%s-%s-%s-%s-%s-%s-%s.plot" % (
            str(k), str(year), str(month), str(day), str(hour), str(minute), plot_id
        )
        absolute_reference = os.path.join(source_drive_config.path, plot_filename)

        return SourcePlot(
            absolute_reference,
            Constants.PLOT_BYTES_BY_K[k]
        )
