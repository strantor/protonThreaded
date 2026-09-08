import os
import time
import subprocess
import pyudev
from PyQt5.QtCore import QThread, pyqtSignal


class USBWatcherWorker(QThread):
    """Background worker thread that monitors USB hardware events."""
    
    # Signals to pass data safely back to the main PyQt/GUI thread
    usb_inserted = pyqtSignal(str, str, list)  # (device_node, mount_point, file_list)
    status_changed = pyqtSignal(str)           # Informational logging signals

    def __init__(self, fallback_mount_point="/mnt/usb", parent=None):
        super().__init__(parent)
        self.fallback_mount_point = fallback_mount_point
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='block', device_type='partition')
        self._is_running = True

    def _get_existing_mount_point(self, dev_node):
        """Checks /proc/mounts to see if device is currently mounted."""
        if not os.path.exists('/proc/mounts'):
            return None
            
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == dev_node:
                    return parts[1]
        return None

    def _mount_device(self, dev_node):
        """Mounts device using system fallback path."""
        os.makedirs(self.fallback_mount_point, exist_ok=True)
        try:
            subprocess.run(["sudo", "mount", dev_node, self.fallback_mount_point], check=True)
            self.status_changed.emit(f"[+] Mounted {dev_node} to {self.fallback_mount_point}")
            return True
        except subprocess.CalledProcessError as e:
            self.status_changed.emit(f"[-] Failed to mount {dev_node}: {e}")
            return False

    def _unmount_device(self):
        """Unmounts fallback directory."""
        subprocess.run(["sudo", "umount", self.fallback_mount_point])
        self.status_changed.emit(f"[+] Unmounted {self.fallback_mount_point}")

    def get_contents(self, mount_point):
        """Returns list of files and folders in mount point."""
        try:
            return os.listdir(mount_point)
        except Exception as e:
            self.status_changed.emit(f"[-] Error reading directory: {e}")
            return []

    def process_usb_partition(self, dev_node):
        """Handles mount checking, directory reading, and signal emission."""
        mount_point = self._get_existing_mount_point(dev_node)
        temp_mounted = False

        if mount_point:
            self.status_changed.emit(f"[i] Drive {dev_node} is already mounted at: {mount_point}")
        else:
            self.status_changed.emit(f"[+] Drive {dev_node} attached. Attempting mount...")
            if self._mount_device(dev_node):
                mount_point = self.fallback_mount_point
                temp_mounted = True
            else:
                return

        # Fetch contents
        files = self.get_contents(mount_point)
        
        # Emit signal to main GUI thread with results
        self.usb_inserted.emit(dev_node, mount_point, files)

        # Cleanup if mounted manually
        if temp_mounted:
            self._unmount_device()

    def check_existing_drives(self):
        """Scans for USB drives already connected at startup."""
        self.status_changed.emit("Checking for existing connected USB drives...")
        found = False
        for device in self.context.list_devices(subsystem='block', DEVTYPE='partition'):
            if device.get('ID_BUS') == 'usb':
                found = True
                dev_node = device.device_node
                self.status_changed.emit(f"[+] Existing USB Partition Found: {dev_node}")
                self.process_usb_partition(dev_node)
                
        if not found:
            self.status_changed.emit("No connected USB drives found on startup.")

    def run(self):
        """QThread entry point. Executes in the background thread."""
        self.check_existing_drives()
        self.status_changed.emit("USBWatcher active: Watching for USB drive insertions...")

        while self._is_running:
            # Poll with 1.0 second timeout to prevent thread blocking on shutdown
            device = self.monitor.poll(timeout=1.0)
            if device and device.action == 'add' and device.get('ID_BUS') == 'usb':
                dev_node = device.device_node
                self.status_changed.emit(f"[+] USB Partition Plugged In: {dev_node}")
                time.sleep(2)
                self.process_usb_partition(dev_node)

    def stop(self):
        """Stops thread execution cleanly."""
        self._is_running = False
        self.wait()  # Wait for QThread loop to exit
        
        
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt USB Watcher Demo")
        self.resize(600, 400)

        # UI Setup
        self.log_box = QTextEdit(self)
        self.log_box.setReadOnly(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.log_box)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Initialize and Start PyQt USB Worker Thread
        self.usb_thread = USBWatcherWorker()
        
        # Connect Signals to Slots (Main UI Thread Functions)
        self.usb_thread.status_changed.connect(self.log_status)
        self.usb_thread.usb_inserted.connect(self.handle_usb_files)
        
        # Start QThread non-blockingly
        self.usb_thread.start()

    def log_status(self, text):
        """Slot: Displays status/logs in UI."""
        self.log_box.append(text)

    def handle_usb_files(self, dev_node, mount_point, file_list):
        """Slot: Triggered when a USB drive's contents are ready."""
        self.log_box.append(f"\n--- CONTENTS OF {dev_node} ---")
        if not file_list:
            self.log_box.append("  (Drive is empty)")
        for f in file_list:
            self.log_box.append(f"  - {f}")
        self.log_box.append("-----------------------------\n")

    def closeEvent(self, event):
        """Stop thread cleanly when window is closed."""
        self.usb_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
