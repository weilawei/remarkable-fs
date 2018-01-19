from contextlib import contextmanager
from collections import namedtuple
from paramiko.client import SSHClient, WarningPolicy
from paramiko.sftp_client import SFTPClient
from paramiko.ssh_exception import AuthenticationException
from getpass import getpass
from signal import signal, SIGTERM, SIGHUP

Connection = namedtuple('Connection', 'ssh sftp')

@contextmanager
def connect():
    with SSHClient() as ssh:
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(WarningPolicy)
        try:
            ssh.connect('10.11.99.1', username="root", look_for_keys=False)
        except AuthenticationException:
            password = getpass()
            ssh.connect('10.11.99.1', username="root", password=password, look_for_keys=False)

        # Stop xochitl but restart it again if the connection drops
        on_start = "systemctl stop xochitl"
        on_finish = "systemctl restart xochitl"
        # We know USB was disconnected when the power supply drops.
        # We also kill the SSH connection so that the information
        # in FUSE is not out of date.
        ssh.exec_command(on_start)
        ssh.exec_command("while udevadm info -p /devices/soc0/soc/2100000.aips-bus/2184000.usb/power_supply/imx_usb_charger | grep -q POWER_SUPPLY_ONLINE=1; do sleep 1; done; %s; kill $PPID" % on_finish)

        try:
            def raise_exception(*args):
                raise RuntimeError("Process terminated")
            signal(SIGTERM, raise_exception)
            signal(SIGHUP, raise_exception)
            with ssh.open_sftp() as sftp:
                yield Connection(ssh, sftp)

        finally:
            # Closing stdin triggers on_finish to run, so only do it now
            print "here"
            try:
                ssh.exec_command(on_finish)
            except:
                pass
