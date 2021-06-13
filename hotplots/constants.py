class Constants:
    # https://github.com/Chia-Network/chia-blockchain/wiki/k-sizes#storage-requirements
    PLOT_BYTES_BY_K = {
        32: 108_880_000_000,  # 101.4 GiB
        33: 224_200_000_000,  # 208.8 GiB
        34: 461_490_000_000,  # 429.8 GiB
        35: 949_300_000_000  # 884.1 GiB
    }

    GIGABYTE = 1_000_000_000
    TERABYTE = 1_000_000_000_000
