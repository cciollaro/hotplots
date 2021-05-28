import yaml

class HotplotsConfig:
    def __init__(self, config_file_path):
        with open(config_file_path, 'r') as stream:
            self.raw_config = yaml.safe_load(stream)

        # TODO: validate config - maybe use dataclasses

    def sources(self):
        return self.raw_config["source_directories"]

    def sleep(self):
        return self.raw_config["sleep"]

    def logging_config(self):
        return self.raw_config["logging"]

    def destinations(self):
        destinations = []

        # TODO: when parsing dirs, make sure they always end in trailing /
        for remote_destination_config in self.raw_config["destinations"]["remote"]:
            for directory in remote_destination_config["directories"]:
                destination = {
                    "type": "remote",
                    "hostname": remote_destination_config["hostname"],
                    "username": remote_destination_config["username"],
                    "port": remote_destination_config["port"],
                    "dir": directory
                }
                destinations.append(destination)

        for directory in self.raw_config["destinations"]["local"]:
            destination = {
                "type": "local",
                "dir": directory
            }
            destinations.append(destination)

        return destinations
