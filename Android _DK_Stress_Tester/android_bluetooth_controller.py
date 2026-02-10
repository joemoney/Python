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
    def __init__(self, file_path, keyword, keyword2, poll_interval=2, timer_duration=5, log_file=None):
        """
        Initialize the Android Bluetooth Controller
        
        Args:
            file_path (str): Path to the text file to monitor (Tera Term output)
            keyword (str): First keyword to search for (triggers BT ON)
            keyword2 (str): Second keyword to search for (triggers timer then BT OFF)
            poll_interval (int): How often to check the file (seconds)
            timer_duration (int): How long to wait before turning off Bluetooth (seconds)
            log_file (str): Path to the log file (optional)
        """
        self.file_path = Path(file_path)
        self.keyword = keyword.lower()
        self.keyword2 = keyword2.lower()
        self.poll_interval = poll_interval
        self.timer_duration = timer_duration
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
                # Try alternative method
                subprocess.run(['adb', 'shell', 'cmd', 'bluetooth_manager', 'enable'],
                             capture_output=True, timeout=5)
                return True
        except Exception as e:
            self.logger.error(f"Error turning on Bluetooth: {e}")
            return False
    
    def get_bluetooth_status(self):
        """Get current Bluetooth status"""
        try:
            result = subprocess.run(['adb', 'shell', 'settings', 'get', 'global', 'bluetooth_on'],
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
    
    def check_keyword2_in_lines(self, lines):
        """Check if second keyword exists in any of the lines"""
        for line in lines:
            if self.keyword2 in line.lower():
                return True, line
        return False, None
    
    def run(self):
        """Main loop to monitor file and control Bluetooth"""
        self.logger.info("=" * 60)
        self.logger.info("Android Bluetooth Controller")
        self.logger.info("=" * 60)
        self.logger.info(f"Monitoring file: {self.file_path}")
        self.logger.info(f"Keyword 1 (BT ON): '{self.keyword}'")
        self.logger.info(f"Keyword 2 (BT OFF): '{self.keyword2}'")
        self.logger.info(f"Poll interval: {self.poll_interval}s")
        self.logger.info(f"Timer duration: {self.timer_duration}s")
        self.logger.info("=" * 60)
        
        # Check ADB connection
        if not self.check_adb_connection():
            return
        
        # Initial Bluetooth off
        self.logger.info(">>> Initial setup: Ensuring Bluetooth is OFF")
        self.bluetooth_off()
        time.sleep(1)
        
        # Check if file is empty and run initialization sequence
        if self.file_path.exists():
            try:
                file_size = self.file_path.stat().st_size
                if file_size == 0:
                    self.logger.info(">>> File is empty - Running initialization sequence")
                    self.logger.info("Turning ON Bluetooth for 3 seconds...")
                    self.bluetooth_on()
                    time.sleep(3)
                    self.logger.info("Turning OFF Bluetooth...")
                    self.bluetooth_off()
                    time.sleep(1)
                    self.logger.info("✓ Initialization sequence complete")
            except Exception as e:
                self.logger.warning(f"Could not check file size: {e}")
        
        self.logger.info(">>> Starting monitoring loop...")
        self.logger.info("Press Ctrl+C to stop")
        
        try:
            total_cycles = 0
            complete_cycles = 0
            timeout_keyword2_cycles = 0
            timeout_2min_keyword1_cycles = 0
            cycle_in_progress = False
            waiting_for_keyword2 = False
            cycle_start_time = None
            bt_on_time = None
            timeout_1min_logged = False
            timeout_2min_reached = False
            
            while True:
                # Read last 5 lines
                last_lines = self.read_last_n_lines(5)
                
                if last_lines:
                    # Check for first keyword
                    keyword_found, matching_line = self.check_keyword_in_lines(last_lines)
                    keyword2_found, matching_line2 = self.check_keyword2_in_lines(last_lines)
                    
                    # Phase 1: Keyword 1 detected -> Turn ON Bluetooth
                    if keyword_found and not cycle_in_progress and not waiting_for_keyword2:
                        total_cycles += 1
                        cycle_in_progress = True
                        cycle_start_time = time.time()
                        timeout_1min_logged = False
                        timeout_2min_reached = False
                        
                        self.logger.info("\n" + "="*60)
                        self.logger.info(f"START OF CYCLE #{total_cycles}")
                        self.logger.info("="*60)
                        self.logger.info(f"Keyword 1 matched: {matching_line}")
                        
                        # Wait 5 seconds before turning ON Bluetooth
                        self.logger.info("⏱ Waiting 5 seconds before turning ON Bluetooth...")
                        time.sleep(5)
                        
                        # Turn ON Bluetooth
                        self.bluetooth_on()
                        time.sleep(2)
                        
                        # Now wait for second keyword
                        waiting_for_keyword2 = True
                        bt_on_time = time.time()
                        self.logger.info(f"Bluetooth ON. Waiting for Keyword 2...")
                    
                    # Keyword 1 detected again while waiting for Keyword 2 - cycle Bluetooth
                    elif keyword_found and waiting_for_keyword2:
                        self.logger.info(f"ℹ Keyword 1 detected again during wait: {matching_line}")
                        self.logger.info(f"Performing Bluetooth cycle: OFF -> wait 30s -> ON")
                        
                        # Turn OFF Bluetooth
                        self.bluetooth_off()
                        time.sleep(2)
                        
                        # Wait 30 seconds
                        self.logger.info("⏱ Waiting 30 seconds...")
                        time.sleep(30)
                        
                        # Turn ON Bluetooth
                        self.bluetooth_on()
                        time.sleep(2)
                        
                        # Reset timer and continue waiting for Keyword 2
                        bt_on_time = time.time()
                        self.logger.info(f"Bluetooth cycled. Continuing to wait for Keyword 2...")
                    
                    # Phase 2: Keyword 2 detected -> Start timer -> Turn OFF Bluetooth
                    elif keyword2_found and waiting_for_keyword2:
                        self.logger.info(f"Keyword 2 matched: {matching_line2}")
                        
                        # Wait timer duration before turning off
                        if self.timer_duration > 0:
                            self.logger.info(f"⏱ Waiting {self.timer_duration} seconds before turning OFF Bluetooth...")
                            time.sleep(self.timer_duration)
                        
                        # Turn OFF Bluetooth
                        self.bluetooth_off()
                        time.sleep(2)
                        
                        complete_cycles += 1
                        self.logger.info(f"✓ Cycle #{total_cycles} COMPLETE. Resuming monitoring...")
                        self.logger.info(f"   [Stats: Complete={complete_cycles}, Timeout_K2(1min)={timeout_keyword2_cycles}, Timeout_K1(10min)={timeout_2min_keyword1_cycles}, Total={total_cycles}]")
                        cycle_in_progress = False
                        waiting_for_keyword2 = False
                
                # Check timeout while waiting for keyword 2 (always check, regardless of file content)
                if waiting_for_keyword2 and bt_on_time:
                    elapsed = time.time() - bt_on_time
                    
                    # Force cycle completion at 10 minute mark (10min timeout on Keyword 1 - extended)
                    if elapsed >= 600 and not timeout_2min_reached:
                        self.logger.warning(f"⚠ 10MIN TIMEOUT: Extended timeout reached in Cycle #{total_cycles}")
                        self.logger.info(f"Proceeding to turn OFF Bluetooth...")
                        timeout_2min_reached = True
                        
                        # Turn OFF Bluetooth
                        self.bluetooth_off()
                        time.sleep(2)
                        
                        timeout_2min_keyword1_cycles += 1
                        self.logger.info(f"✓ Cycle #{total_cycles} complete (10MIN TIMEOUT on Keyword 1). Resuming monitoring...")
                        self.logger.info(f"   [Stats: Complete={complete_cycles}, Timeout_K2(1min)={timeout_keyword2_cycles}, Timeout_K1(10min)={timeout_2min_keyword1_cycles}, Total={total_cycles}]")
                        cycle_in_progress = False
                        waiting_for_keyword2 = False
                    
                    # Log warning at 5 minute mark
                    elif elapsed >= 300 and not timeout_1min_logged and not timeout_2min_reached:
                        self.logger.warning(f"⚠ 5MIN WARNING: Keyword 2 not detected for 5 minutes in Cycle #{total_cycles}")
                        self.logger.info(f"Will continue waiting until 10 minute timeout...")
                        timeout_1min_logged = True
                    
                    # Turn off at 1 minute mark (Keyword 2 timeout)
                    elif elapsed >= 60 and not timeout_1min_logged:
                        self.logger.warning(f"⚠ TIMEOUT: Keyword 2 not detected for 1 minute in Cycle #{total_cycles}")
                        self.logger.info(f"Proceeding to turn OFF Bluetooth...")
                        timeout_1min_logged = True
                        
                        # Turn OFF Bluetooth
                        self.bluetooth_off()
                        time.sleep(2)
                        
                        timeout_keyword2_cycles += 1
                        self.logger.info(f"✓ Cycle #{total_cycles} complete (TIMEOUT on Keyword 2). Resuming monitoring...")
                        self.logger.info(f"   [Stats: Complete={complete_cycles}, Timeout_K2(1min)={timeout_keyword2_cycles}, Timeout_K1(10min)={timeout_2min_keyword1_cycles}, Total={total_cycles}]")
                        cycle_in_progress = False
                        waiting_for_keyword2 = False
                
                # Wait before next poll
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            self.logger.info("\n>>> Stopping controller...")
            self.logger.info("="*60)
            self.logger.info("FINAL STATISTICS")
            self.logger.info("="*60)
            self.logger.info(f"Total cycles started: {total_cycles}")
            self.logger.info(f"Complete cycles (both keywords found): {complete_cycles}")
            self.logger.info(f"Timeout on Keyword 2 (1 min): {timeout_keyword2_cycles}")
            self.logger.info(f"10min Timeout on Keyword 1: {timeout_2min_keyword1_cycles}")
            self.logger.info(f"Success rate: {(complete_cycles/total_cycles*100) if total_cycles > 0 else 0:.1f}%")
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
  python android_bluetooth_controller.py -f C:\\logs\\teraterm.log -k "ready" -p 3 -t 10
  
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
    parser.add_argument('-k2', '--keyword2',
                       required=True,
                       help='Second keyword to search for (triggers timer then Bluetooth OFF)')
    parser.add_argument('-p', '--poll-interval',
                       type=int,
                       default=2,
                       help='Polling interval in seconds (default: 2)')
    parser.add_argument('-t', '--timer',
                       type=int,
                       default=5,
                       help='Timer duration in seconds before turning on Bluetooth (default: 5)')
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
        keyword2=args.keyword2,
        poll_interval=args.poll_interval,
        timer_duration=args.timer,
        log_file=args.log_file
    )
    
    controller.run()


if __name__ == '__main__':
    main()
