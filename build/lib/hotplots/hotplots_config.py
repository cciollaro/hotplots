import sys
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class LoggingFileConfig:
    enabled: bool = False
    path: str = "hotplots.log"


@dataclass(frozen=True)
class LoggingStdoutConfig:
    enabled: bool = True


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    stdout: LoggingStdoutConfig = LoggingStdoutConfig()
    file: LoggingFileConfig = LoggingFileConfig()


@dataclass(frozen=True)
class SourceDriveConfig:
    path: str
    max_concurrent_outbound_transfers: int = 1


@dataclass(frozen=True)
class SourceConfig:
    drives: List[SourceDriveConfig]
    check_source_drives_sleep_seconds: int = 60
    selection_strategy: str = "least_available_space"


@dataclass(frozen=True)
class PlotReplacementConfig:
    enabled: bool = False
    type: str = ""
    value: str = ""


@dataclass(frozen=True)
class TargetDriveConfig:
    path: str
    max_concurrent_inbound_transfers: int
    plot_replacement: PlotReplacementConfig = PlotReplacementConfig()


@dataclass(frozen=True)
class LocalHostConfig:
    drives: List[TargetDriveConfig]

    # local host doesn't have a max concurrent inbound transfers, but for parity
    # with remote hosts we'll just set it essentially to infinity.
    def __post_init__(self):
        object.__setattr__(self, 'max_concurrent_inbound_transfers', sys.maxsize)

    def is_local(self):
        return True

    def get_hostname(self):
        return "localhost"

@dataclass(frozen=True)
class RemoteHostConfig:
    hostname: str
    username: str
    port: int
    max_concurrent_inbound_transfers: int
    drives: List[TargetDriveConfig]

    def is_local(self):
        return False

    def get_hostname(self):
        return self.hostname


@dataclass(frozen=True)
class RemoteTargetsConfig:
    max_concurrent_outbound_transfers: int
    hosts: List[RemoteHostConfig]


@dataclass(frozen=True)
class TargetsConfig:
    selection_strategy: str
    local: LocalHostConfig
    remote: RemoteTargetsConfig
    target_host_preference: str = "local"


@dataclass(frozen=True)
class HotplotsConfig:
    logging: LoggingConfig
    source: SourceConfig
    targets: TargetsConfig
