class HotplotsConfig:
    def __init__(self, yaml_file_contents):
        self.config = {
            "source_directories": yaml_file_contents["source_directories"],
            "destinations": []
        }

        # TODO: when parsing dirs, make sure they always end in trailing /
        for remote_destination_config in yaml_file_contents["destinations"]["remote"]:
            for directory in remote_destination_config["directories"]:
                destination = {
                    "type": "remote",
                    "hostname": remote_destination_config["hostname"],
                    "username": remote_destination_config["username"],
                    "port": remote_destination_config["port"],
                    "dir": directory
                }
                self.config["destinations"].append(destination)

        for directory in yaml_file_contents["destinations"]["local"]:
            destination = {
                "type": "local",
                "dir": directory
            }
            self.config["destinations"].append(destination)

    def sources(self):
        return self.config["source_directories"]

    def destinations(self):
        return self.config["destinations"]