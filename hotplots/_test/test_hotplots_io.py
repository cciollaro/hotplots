import unittest
from unittest.mock import patch, MagicMock, ANY

from hotplots.hotplots_io import HotplotsIO
from hotplots.models import HotPlot, HotPlotTargetDrive, SourcePlot, TargetDriveInfo, LocalHostConfig, RemoteHostConfig, TargetDriveConfig


class TestHotplotsIO(unittest.TestCase):

    def setUp(self):
        self.hotplots_io = HotplotsIO()
        self.source_plot = SourcePlot(absolute_reference='/source/plot-k32-2021-06-01-00-00-dummyid.plot', size=123)
        self.hot_plot = HotPlot(source_drive_info=MagicMock(), source_plot=self.source_plot)

    @patch('os.remove')
    @patch('os.rename')
    @patch('shutil.copy2')
    def test_transfer_plot_local_success(self, mock_copy, mock_rename, mock_remove):
        # Arrange
        target_drive_config = TargetDriveConfig(path='/target', max_concurrent_inbound_transfers=1)
        target_drive_info = TargetDriveInfo(target_drive_config=target_drive_config, total_bytes=1, free_bytes=1, in_flight_transfers=[])
        local_host_config = LocalHostConfig(drives=[target_drive_config])
        hot_plot_target_drive = HotPlotTargetDrive(host_config=local_host_config, target_drive_info=target_drive_info)

        # Act
        self.hotplots_io.transfer_plot(self.hot_plot, hot_plot_target_drive)

        # Assert
        mock_copy.assert_called_once_with('/source/plot-k32-2021-06-01-00-00-dummyid.plot', ANY)
        self.assertTrue(mock_copy.call_args[0][1].startswith('/target/.plot-k32-2021-06-01-00-00-dummyid.plot'))
        mock_rename.assert_called_once_with(ANY, '/target/plot-k32-2021-06-01-00-00-dummyid.plot')
        self.assertTrue(mock_rename.call_args[0][0].startswith('/target/.plot-k32-2021-06-01-00-00-dummyid.plot'))
        mock_remove.assert_called_once_with('/source/plot-k32-2021-06-01-00-00-dummyid.plot')

    @patch('os.path.exists', return_value=True)
    @patch('os.remove')
    @patch('shutil.copy2', side_effect=Exception("Disk full"))
    def test_transfer_plot_local_failure_cleanup(self, mock_copy, mock_remove, mock_exists):
        # Arrange
        target_drive_config = TargetDriveConfig(path='/target', max_concurrent_inbound_transfers=1)
        target_drive_info = TargetDriveInfo(target_drive_config=target_drive_config, total_bytes=1, free_bytes=1, in_flight_transfers=[])
        local_host_config = LocalHostConfig(drives=[target_drive_config])
        hot_plot_target_drive = HotPlotTargetDrive(host_config=local_host_config, target_drive_info=target_drive_info)

        # Act & Assert
        with self.assertRaises(Exception):
            self.hotplots_io.transfer_plot(self.hot_plot, hot_plot_target_drive)

        mock_copy.assert_called_once()
        # The first call to remove is the cleanup of the temp file
        mock_remove.assert_called_once_with(ANY)
        self.assertTrue(mock_remove.call_args[0][0].startswith('/target/.plot-k32-2021-06-01-00-00-dummyid.plot'))

    @patch('os.remove')
    @patch('paramiko.SSHClient')
    @patch('socket.gethostbyname', return_value='1.2.3.4')
    def test_transfer_plot_remote_success(self, mock_gethostbyname, mock_ssh_client, mock_os_remove):
        # Arrange
        mock_sftp = MagicMock()
        mock_ssh_client.return_value.open_sftp.return_value = mock_sftp

        target_drive_config = TargetDriveConfig(path='/remote/target', max_concurrent_inbound_transfers=1)
        target_drive_info = TargetDriveInfo(target_drive_config=target_drive_config, total_bytes=1, free_bytes=1, in_flight_transfers=[])
        remote_host_config = RemoteHostConfig(hostname='remote-host', port=22, username='user', drives=[target_drive_config], max_concurrent_inbound_transfers=1)
        hot_plot_target_drive = HotPlotTargetDrive(host_config=remote_host_config, target_drive_info=target_drive_info)

        # Act
        self.hotplots_io.transfer_plot(self.hot_plot, hot_plot_target_drive)

        # Assert
        mock_ssh_client.return_value.connect.assert_called_once_with('1.2.3.4', port=22, username='user')
        mock_sftp.put.assert_called_once_with('/source/plot-k32-2021-06-01-00-00-dummyid.plot', ANY)
        self.assertTrue(mock_sftp.put.call_args[0][1].startswith('/remote/target/.plot-k32-2021-06-01-00-00-dummyid.plot'))
        mock_sftp.rename.assert_called_once_with(ANY, '/remote/target/plot-k32-2021-06-01-00-00-dummyid.plot')
        self.assertTrue(mock_sftp.rename.call_args[0][0].startswith('/remote/target/.plot-k32-2021-06-01-00-00-dummyid.plot'))
        mock_os_remove.assert_called_once_with('/source/plot-k32-2021-06-01-00-00-dummyid.plot')
        mock_sftp.close.assert_called_once()
        mock_ssh_client.return_value.close.assert_called_once()

    @patch('os.remove')
    @patch('paramiko.SSHClient')
    @patch('socket.gethostbyname', return_value='1.2.3.4')
    def test_transfer_plot_remote_failure_cleanup(self, mock_gethostbyname, mock_ssh_client, mock_os_remove):
        # Arrange
        mock_sftp = MagicMock()
        mock_sftp.put.side_effect = Exception("Connection lost")
        mock_ssh_client.return_value.open_sftp.return_value = mock_sftp

        target_drive_config = TargetDriveConfig(path='/remote/target', max_concurrent_inbound_transfers=1)
        target_drive_info = TargetDriveInfo(target_drive_config=target_drive_config, total_bytes=1, free_bytes=1, in_flight_transfers=[])
        remote_host_config = RemoteHostConfig(hostname='remote-host', port=22, username='user', drives=[target_drive_config], max_concurrent_inbound_transfers=1)
        hot_plot_target_drive = HotPlotTargetDrive(host_config=remote_host_config, target_drive_info=target_drive_info)

        # Act & Assert
        with self.assertRaises(Exception):
            self.hotplots_io.transfer_plot(self.hot_plot, hot_plot_target_drive)

        mock_sftp.put.assert_called_once()
        mock_sftp.remove.assert_called_once_with(ANY)
        self.assertTrue(mock_sftp.remove.call_args[0][0].startswith('/remote/target/.plot-k32-2021-06-01-00-00-dummyid.plot'))
        mock_os_remove.assert_not_called()
        mock_sftp.close.assert_called_once()
        mock_ssh_client.return_value.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
