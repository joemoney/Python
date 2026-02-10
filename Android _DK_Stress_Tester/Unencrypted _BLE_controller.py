"""
Android Bluetooth Controller
Monitors a text file (Tera Term output) and controls Android device Bluetooth via ADB
"""

import subprocess
import time
import os
import logging
from pathlib import Path
from datetime import datetime

class AndroidBluetoothController:
    def __init__(self, file_path, keyword, poll_interval=2, log_file=None):
        """
        Initialize the Android Bluetooth Controller
        
        Args:
            file_path (str): Path to the text file to monitor (Tera Term output)
            keyword (str): First keyword to search for (triggers BT ON)
            poll_interval (int): How often to check the file (seconds)
            log_file (str): Path to the log file (optional)
        """
        self.file_path = Path(file_path)
        self.keyword = keyword.lower()
        self.poll_interval = poll_interval
        self.last_file_size = 0
        self.logger = self._setup_logging(log_file)
    
    def _setup_logging(self, log_file):
        """Setup logging to file and console"""
        logger = logging.getLogger('AndroidBluetoothController')
        logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Create custom formatter with local time
        class LocalTimeFormatter(logging.Formatter):
            converter = time.localtime
        
        formatter = LocalTimeFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (if log file specified)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        
        return logger
        
    def check_adb_connection(self):
        """Check if ADB device is connected"""
        try:
            # First, try to start ADB server if not running
            self.logger.info("Checking ADB server...")
            subprocess.run(['adb', 'start-server'], 
                          capture_output=True, 
                          timeout=10)
            time.sleep(1)
            
            # Now check for devices
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            lines = result.stdout.strip().split('\n')
            # Check if there's at least one device connected
            devices = [line for line in lines[1:] if '\tdevice' in line]
            if not devices:
                self.logger.error("No Android device detected via ADB")
                self.logger.error("Please ensure USB debugging is enabled and device is connected")
                return False
            self.logger.info(f"✓ Android device connected: {devices[0].split()[0]}")
            return True
        except FileNotFoundError:
            self.logger.error("ADB not found. Please install Android SDK Platform Tools")
            self.logger.error("Download from: https://developer.android.com/studio/releases/platform-tools")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("ADB command timed out. Try running 'adb kill-server' then 'adb start-server' manually")
            return False
        except Exception as e:
            self.logger.error(f"Error checking ADB connection: {e}")
            return False
    
    def bluetooth_off(self):
        """Turn off Bluetooth on Android device"""
        try:
            self.logger.info("Turning OFF Bluetooth...")
            result = subprocess.run(['adb', 'shell', 'svc', 'bluetooth', 'disable'],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                self.logger.info("✓ Bluetooth turned OFF")
                return True
            else:
                self.logger.warning(f"Bluetooth disable command returned code {result.returncode}")
                # Try alternative method
                subprocess.run(['adb', 'shell', 'cmd', 'bluetooth_manager', 'disable'],
                             capture_output=True, timeout=5)
                return True
        except Exception as e:
            self.logger.error(f"Error turning off Bluetooth: {e}")
            return False

    def bluetooth_on(self):
        """Turn on Bluetooth on Android device"""
        try:
            self.logger.info("Turning ON Bluetooth...")
            result = subprocess.run(['adb', 'shell', 'svc', 'bluetooth', 'enable'],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                self.logger.info("✓ Bluetooth turned ON")
                return True
            else:
                self.logger.warning(f"Bluetooth enable command returned code {result.returncode}")
                subprocess.run(['adb', 'shell', 'cmd', 'bluetooth_manager', 'enable'],
                             capture_output=True, timeout=5)
                return True
        except Exception as e:
            self.logger.error(f"Error turning on Bluetooth: {e}")
            return False
    
    def start_connecting(self):
        """Start BLE connect service on Android device"""
        try:
            self.logger.info("Starting BLE connect service...")
            result = subprocess.run([
                'adb', 'shell', 'am', 'startservice',
                '-a', 'com.example.bletestapp.CONNECT_PERIPHERAL',
                '--es', 'irk', '42366578927e0ecdab9cfac1f77400e5'
            ],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                self.logger.info("✓ BLE connect service started")
                return True
            else:
                self.logger.warning(f"BLE connect service command returned code {result.returncode}")
                return False
        except Exception as e:
            self.logger.error(f"Error starting BLE connect service: {e}")
            return False
    
    def get_bluetooth_status(self):
        """Get current Bluetooth status"""
        try:
            result = subprocess.run(['adb', 'shell', 'settings', 'get', 'global', 'start_connecting'],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            status = result.stdout.strip()
            return status == '1'
        except Exception as e:
            self.logger.warning(f"Could not get Bluetooth status: {e}")
            return None
    
    def read_last_n_lines(self, n=5):
        """Read the last N lines from the file (non-locking read for shared access)"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                if not self.file_path.exists():
                    return []
                
                # Open with shared access - allows other processes to write while we read
                # Using 'r' mode with 'with' statement ensures file is closed immediately
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read all lines
                    lines = f.readlines()
                    # Return last N lines, stripped of whitespace
                    return [line.strip() for line in lines[-n:] if line.strip()]
                    
            except PermissionError:
                # File might be temporarily locked by the writing process
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    self.logger.warning(f"Permission denied reading file after {max_retries} attempts")
                    return []
                    
            except (IOError, OSError) as e:
                # Handle other I/O errors (file being written, etc.)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    self.logger.error(f"I/O error reading file: {e}")
                    return []
                    
            except Exception as e:
                self.logger.error(f"Error reading file: {e}")
                return []
        
        return []
    
    def check_keyword_in_lines(self, lines):
        """Check if keyword exists in any of the lines"""
        for line in lines:
            if self.keyword in line.lower():
                return True, line
        return False, None
    
    def run(self):
        """Main loop to monitor file and control Bluetooth"""
        self.logger.info("=" * 60)
        self.logger.info("Android Bluetooth Controller")
        self.logger.info("=" * 60)
        self.logger.info(f"Monitoring file: {self.file_path}")
        self.logger.info(f"Keyword 1 (start connect): '{self.keyword}'")
        self.logger.info(f"Poll interval: {self.poll_interval}s")
        self.logger.info("=" * 60)
        
        # Check ADB connection
        if not self.check_adb_connection():
            return
        
        # Initial Bluetooth on
        self.logger.info(">>> Initial setup: Turning Bluetooth ON")
        self.bluetooth_on()
        time.sleep(1)

        # Check if file is empty and run initialization sequence
        if self.file_path.exists():
            try:
                file_size = self.file_path.stat().st_size
                if file_size == 0:
                    self.logger.info(">>> File is empty - Running initialization sequence")
                    self.logger.info("Starting connect service for 3 seconds...")
                    self.start_connecting()
                    time.sleep(3)
                    self.logger.info("✓ Initialization sequence complete")
            except Exception as e:
                self.logger.warning(f"Could not check file size: {e}")
        
        self.logger.info(">>> Starting monitoring loop...")
        self.logger.info("Press Ctrl+C to stop")
        
        try:
            total_cycles = 0
            last_trigger_line = None
            last_keyword_time = time.time()
            
            while True:
                # Read last 5 lines
                last_lines = self.read_last_n_lines(5)
                
                if last_lines:
                    # Check for first keyword
                    keyword_found, matching_line = self.check_keyword_in_lines(last_lines)
                    # Keyword 1 detected -> Start BLE connect service
                    if keyword_found and matching_line != last_trigger_line:
                        total_cycles += 1
                        last_trigger_line = matching_line
                        last_keyword_time = time.time()
                        
                        self.logger.info("\n" + "="*60)
                        self.logger.info(f"START OF CYCLE #{total_cycles}")
                        self.logger.info("="*60)
                        self.logger.info(f"Keyword 1 matched: {matching_line}")
                        
                        # Wait 5 seconds before starting a new connection
                        self.logger.info("⏱ Waiting 5 seconds before starting a new connection...")
                        time.sleep(5)
                        
                        # Start BLE connect service
                        self.start_connecting()
                        time.sleep(2)

                # Timeout: no keyword for 10 minutes -> start connect service anyway
                if time.time() - last_keyword_time >= 600:
                    total_cycles += 1
                    last_keyword_time = time.time()
                    self.logger.info("\n" + "="*60)
                    self.logger.info(f"START OF CYCLE #{total_cycles}")
                    self.logger.info("="*60)
                    self.logger.warning("⚠ 10MIN TIMEOUT: No keyword detected. Starting connect service anyway.")
                    self.logger.info("⏱ Waiting 5 seconds before starting a new connection...")
                    time.sleep(5)
                    self.start_connecting()
                    time.sleep(2)
                
                # Wait before next poll
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            self.logger.info("\n>>> Stopping controller...")
            self.logger.info("="*60)
            self.logger.info("FINAL STATISTICS")
            self.logger.info("="*60)
            self.logger.info(f"Total cycles started: {total_cycles}")
            self.logger.info("="*60)
            self.logger.info("Goodbye!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor a text file and control Android Bluetooth via ADB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
    python android_bluetooth_controller.py -f output.txt -k "ERROR"
    python android_bluetooth_controller.py -f C:\\logs\\teraterm.log -k "ready" -p 3
  
Requirements:
  - Android device connected via USB
  - USB debugging enabled on Android device
  - ADB (Android Debug Bridge) installed and in PATH
        """
    )
    
    parser.add_argument('-f', '--file', 
                       required=True,
                       help='Path to the text file to monitor (Tera Term output)')
    parser.add_argument('-k', '--keyword',
                       required=True,
                       help='First keyword to search for (triggers Bluetooth ON)')
    parser.add_argument('-p', '--poll-interval',
                       type=int,
                       default=2,
                       help='Polling interval in seconds (default: 2)')
    parser.add_argument('-l', '--log-file',
                       default='android_bt_controller.log',
                       help='Path to log file (default: android_bt_controller.log)')
    
    args = parser.parse_args()
    
    # Validate file path
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"WARNING: File '{file_path}' does not exist yet.")
        print("The script will wait for it to be created...\n")
    
    # Create and run controller
    controller = AndroidBluetoothController(
        file_path=args.file,
        keyword=args.keyword,
        poll_interval=args.poll_interval,
        log_file=args.log_file
    )
    
    controller.run()


if __name__ == '__main__':
    main()
