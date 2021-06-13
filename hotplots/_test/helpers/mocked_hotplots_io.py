from hotplots.hotplots_config import SourceConfig, SourceDriveConfig, LocalHostConfig, RemoteTargetsConfig
from hotplots.hotplots_io import HotplotsIO
from hotplots.models import SourceInfo, SourceDriveInfo, LocalTargetsInfo, RemoteTargetsInfo, TargetDriveInfo

class MockedHotplotsIO(HotplotsIO):
    source_drive_info_generator = {
        "/mnt/source1": lambda sdc: SourceDriveInfo(sdc, 1*TERABYTE, 1*TERABYTE, [])
    }

    target_drive_info_generator = {
        "/mnt/local_target1": lambda tdc: TargetDriveInfo(tdc, 1*TERABYTE, 1*TERABYTE, [])
    }

    def get_source_info(self, source_config: SourceConfig) -> SourceInfo:
        source_drive_infos = [
            self.source_drive_info_generator[x.path](x) for x in source_config.drives
        ]
        return SourceInfo(source_config, source_drive_infos=source_drive_infos)

    def get_local_target_info(self, local_target_config: LocalHostConfig) -> LocalTargetsInfo:
        target_drive_infos = [
            self.target_drive_info_generator[x.path](x) for x in local_target_config.drives
        ]
        return LocalTargetsInfo(local_target_config, target_drive_infos)

    # no remote for now.
    def get_remote_targets_info(self, remote_targets_config: RemoteTargetsConfig) -> RemoteTargetsInfo:
        return RemoteTargetsInfo(remote_targets_config, [])




