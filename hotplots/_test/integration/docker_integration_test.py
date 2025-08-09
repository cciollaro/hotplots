import unittest
import os
import threading
import time
from pathlib import Path
import subprocess
import yaml

import paramiko

from hotplots._test.integration.integration_test_helpers import HotplotsIntegrationTestBase


class DockerIntegrationTest(HotplotsIntegrationTestBase):
    def setUp(self):
        super().setUp()
        self.ssh_host = "sshd"
        self.ssh_port = 22
        self.ssh_user = "sshuser"
        # This password is for the initial setup. The test will use key-based auth.
        self.ssh_password = "password"
        # Paths within the containers
        # Use the temporary source directory from the base class so the source
        # plots are not automatically visible on the remote host. The remote
        # host stores plots in its own target directory.
        self.target_path_on_remote = Path("/home/sshuser/target")

        # Clean up previous test runs
        self.cleanup_remote_target()

        # Generate a temporary SSH key for the test
        self.ssh_key_path = self.temp_dir.name / Path("id_rsa")
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(self.ssh_key_path)
        self.ssh_public_key = f"{key.get_name()} {key.get_base64()}"

        # Set up the SSH client
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the sshd container to set up the public key
        self.ssh_client.connect(
            self.ssh_host,
            port=self.ssh_port,
            username=self.ssh_user,
            password=self.ssh_password,
            allow_agent=False,
            look_for_keys=False
        )
        self.ssh_client.exec_command(f"echo '{self.ssh_public_key}' >> /home/sshuser/.ssh/authorized_keys")
        self.ssh_client.exec_command("chmod 600 /home/sshuser/.ssh/authorized_keys")
        self.ssh_client.close()

    def cleanup_remote_target(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                self.ssh_host,
                port=self.ssh_port,
                username=self.ssh_user,
                password=self.ssh_password,
                allow_agent=False,
                look_for_keys=False
            )
            sftp = client.open_sftp()
            for filename in sftp.listdir(str(self.target_path_on_remote)):
                sftp.remove(str(self.target_path_on_remote / filename))
            sftp.close()
            client.close()
        except Exception as e:
            # It's okay if this fails (e.g., on the first run)
            print(f"Could not clean up remote target: {e}")


    def test_remote_move(self):
        plot_filename = "plot-k32-2021-06-01-00-00-dummyid.plot"
        # Create the dummy plot in the local source directory
        local_source_path = self.source_path / plot_filename
        with open(local_source_path, "w") as f:
            f.write("dummy plot data")

        config = {
            "logging": {
                "level": "DEBUG",
                "stdout": {"enabled": True},
                "file": {"enabled": False},
            },
            "source": {
                "check_source_drives_sleep_seconds": 1,
                "selection_strategy": "plot_with_oldest_timestamp",
                "drives": [{"path": str(self.source_path), "max_concurrent_outbound_transfers": 1}],
            },
            "targets": {
                "target_host_preference": "remote",
                "selection_strategy": "drive_with_most_space_remaining",
                "local": {"drives": []},
                "remote": {
                    "max_concurrent_outbound_transfers": 1,
                    "hosts": [
                        {
                            "hostname": self.ssh_host,
                            "port": self.ssh_port,
                            "username": self.ssh_user,
                            "key_path": str(self.ssh_key_path),
                            "max_concurrent_inbound_transfers": 1,
                            "drives": [
                                {
                                    "path": str(self.target_path_on_remote),
                                    "max_concurrent_inbound_transfers": 1,
                                }
                            ],
                        }
                    ],
                },
            },
        }

        config_path = self.temp_dir.name / Path("config.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Run hotplots in a separate process
        process = subprocess.Popen(
            ["hotplots", "--config", str(config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Give hotplots some time to move the file
        time.sleep(5)
        process.terminate() # hotplots runs in a loop, so we need to kill it

        # Assertions
        # The source file should be gone
        self.assertFalse(os.path.exists(local_source_path))

        # The target file should exist on the remote host
        self.ssh_client.connect(
            self.ssh_host,
            port=self.ssh_port,
            username=self.ssh_user,
            pkey=paramiko.RSAKey.from_private_key_file(str(self.ssh_key_path)),
            allow_agent=False,
            look_for_keys=False
        )
        sftp = self.ssh_client.open_sftp()
        try:
            sftp.stat(str(self.target_path_on_remote / plot_filename))
        except FileNotFoundError:
            self.fail("File not found on remote target")
        finally:
            sftp.close()
            self.ssh_client.close()

if __name__ == '__main__':
    unittest.main()
