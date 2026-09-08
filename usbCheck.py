import os
import time
import subprocess
import pyudev


class USBWatcher:
    def __init__(self, fallback_mount_point="/mnt/usb"):
        self.fallback_mount_point = fallback_mount_point
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='block')
        self.mountPoint = ""
        self.usbMounted = False

    def _get_existing_mount_point(self, dev_node):
        """Checks /proc/mounts to see if the device node is currently mounted."""
        if not os.path.exists('/proc/mounts'):
            return None

        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == dev_node:
                    return parts[1]
        return None

    def _mount_device(self, dev_node):
        """Mounts the device to the fallback path if not auto-mounted."""
        os.makedirs(self.fallback_mount_point, exist_ok=True)
        try:
            subprocess.run(["sudo", "mount", dev_node, self.fallback_mount_point], check=True)
            print(f"[+] Mounted {dev_node} to {self.fallback_mount_point}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to mount {dev_node}: {e}")
            return False

    def _unmount_device(self):
        """Unmounts the fallback directory."""
        subprocess.run(["sudo", "umount", self.fallback_mount_point])
        print(f"[+] Unmounted {self.fallback_mount_point}")

    def list_contents(self, mount_point):
        """Lists files and folders inside the mount path."""
        print(f"--- Contents of ({mount_point}) ---")
        try:
            files = os.listdir(mount_point)
            if not files:
                print("  (Drive is empty)")
            for item in files:
                print(f"  - {item}")
        except Exception as e:
            print(f"[-] Error reading directory: {e}")

    def process_usb_partition(self, dev_node):
        """Handles checking mount status and printing contents for a USB partition."""
        mount_point = self._get_existing_mount_point(dev_node)
        temp_mounted = False

        if mount_point:
            print(f"[i] Drive {dev_node} is already mounted at: {mount_point}")
            self.usbMounted = True
            self.mountPoint = mount_point
        else:
            print(f"[+] Drive {dev_node} is attached but not mounted. Attempting mount...")
            if self._mount_device(dev_node):
                mount_point = self.fallback_mount_point
                temp_mounted = True
            else:
                return

        # Read contents
        self.list_contents(mount_point)

        # Cleanup if we mounted it manually
        if temp_mounted:
            self._unmount_device()

    def check_existing_drives(self):
        """Scans for USB drives already connected at startup."""
        print("Checking for existing connected USB drives...")
        found = False
        for device in self.context.list_devices(subsystem='block'):
            if device.get('ID_BUS') == 'usb':
                found = True
                dev_node = device.device_node
                print(f"\n[+] Existing USB Partition Found: {dev_node}")
                self.process_usb_partition(dev_node)

        if not found:
            print("No connected USB drives found on startup.")

    def start_listening(self):
        """Checks initial state, then watches for real-time insertions."""
        # 1. Handle drives already plugged in
        self.check_existing_drives()

        # 2. Start monitoring for new insertions
        print("\nWaiting for USB drive insertion...")
        for device in iter(self.monitor.poll, None):
            if device.action == 'add' and device.get('ID_BUS') == 'usb':
                dev_node = device.device_node
                print(f"\n[+] USB Partition Plugged In: {dev_node}")
                time.sleep(2)  # Give system mounter time
                self.process_usb_partition(dev_node)
            elif device.action == 'remove':
                print(f"USB Removed: {device.device_node}")
                self.mountPoint = ""
                self.usbMounted = False


if __name__ == "__main__":
    watcher = USBWatcher()
    watcher.start_listening()
