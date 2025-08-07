class Constants:
    # Since we don't get the disk usage information and the staged plot file size information at the same moment (they're
    # done in separate calls), we add a 5% error term to the staged file size as insurance against over-committing a drive
    # and filling it up, which is a very bad outcome.
    # 5% is not empirically tested at all, it's just a value that I figure should be enough.
    # In the case that the 5% causes a false negative, it'll eventually be rectified once transfers on the drive complete,
    # which is a much less bad outcome than filling the drive. Reducing the 5% here will reduce the false negative rate, but
    # at some point it will introduce false positives (over-commit case) so reduce with caution.
    STAGED_FILES_ERROR_TERM = 1.05

    # https://github.com/Chia-Network/chia-blockchain/wiki/k-sizes#storage-requirements
    PLOT_BYTES_BY_K = {
        32: 108_880_000_000,  # 101.4 GiB
        33: 224_200_000_000,  # 208.8 GiB
        34: 461_490_000_000,  # 429.8 GiB
        35: 949_300_000_000  # 884.1 GiB
    }

    # Is there no better way to do this?
    GIGABYTE = 1_000_000_000
    TERABYTE = 1_000_000_000_000
