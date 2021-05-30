from dataclasses import dataclass
from enum import Enum

#TODO: when doing math to decide whether to start another transfer, always use a sizeable safety buffer..
# an incorrect "not eligible" is better than an incorrect "eligible" because we we'll freeze up multiple transfers
# in the "not eligible" case, but in the "eligible" case it'll be corrected once the current transfer
# finishes.
class HotplotsEngine:
    @staticmethod
    def decide(config, source_info, local_targets, remote_targets):
        pass
        # Step 1: figure out if we have any hot plots

        # Step 2: figure out if we can transfer it anywhere

        # Step 3: if not, should we delete another plot to make room for it?

        # Step 4: process actions

@dataclass
class GetTransferActionsResult:
    pass

@dataclass
class GetTransferActionResultStatus(Enum):
    pass