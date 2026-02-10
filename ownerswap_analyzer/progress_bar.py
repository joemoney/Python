"""
Progress Bar Plugin for Python Applications

This module provides a flexible progress bar implementation that can be used
to track progress of long-running operations like file processing, data analysis, etc.

Features:
- Customizable progress bar appearance
- Multiple display styles (bar, percentage, spinner)
- Time estimation and speed calculation
- Memory efficient for large datasets
- Thread-safe operations
"""

import time
import sys
import threading
from typing import Optional, Callable, Any


class ProgressBar:
    """
    A flexible progress bar implementation with multiple display options.
    
    Example usage:
        # Basic usage
        progress = ProgressBar(total=100, description="Processing")
        for i in range(100):
            # Do some work
            progress.update(1)
        progress.close()
        
        # Context manager usage
        with ProgressBar(total=100, description="Processing") as progress:
            for i in range(100):
                # Do some work
                progress.update(1)
    """
    
    def __init__(self, 
                 total: int, 
                 description: str = "Progress",
                 bar_length: int = 50,
                 show_percentage: bool = True,
                 show_count: bool = True,
                 show_rate: bool = True,
                 show_eta: bool = True,
                 bar_format: str = "█",
                 empty_format: str = "░",
                 file=None):
        """
        Initialize the progress bar.
        
        Args:
            total: Total number of items to process
            description: Description text to display
            bar_length: Length of the progress bar in characters
            show_percentage: Whether to show percentage complete
            show_count: Whether to show current/total count
            show_rate: Whether to show processing rate
            show_eta: Whether to show estimated time to completion
            bar_format: Character to use for completed portion
            empty_format: Character to use for empty portion
            file: Output stream (default: sys.stdout)
        """
        self.total = total
        self.description = description
        self.bar_length = bar_length
        self.show_percentage = show_percentage
        self.show_count = show_count
        self.show_rate = show_rate
        self.show_eta = show_eta
        self.bar_format = bar_format
        self.empty_format = empty_format
        self.file = file or sys.stdout
        
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.lock = threading.Lock()
        self._closed = False
        
    def update(self, n: int = 1):
        """
        Update the progress bar by n steps.
        
        Args:
            n: Number of steps to advance (default: 1)
        """
        with self.lock:
            if self._closed:
                return
                
            self.current = min(self.current + n, self.total)
            current_time = time.time()
            
            # Only update display if enough time has passed (reduce flickering)
            if current_time - self.last_update_time >= 0.1 or self.current >= self.total:
                self._display()
                self.last_update_time = current_time
    
    def set_progress(self, value: int):
        """
        Set the current progress to a specific value.
        
        Args:
            value: The current progress value
        """
        with self.lock:
            if self._closed:
                return
                
            self.current = min(max(value, 0), self.total)
            self._display()
    
    def _display(self):
        """Internal method to display the current progress."""
        if self._closed:
            return
            
        # Calculate percentage
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        
        # Create progress bar
        filled_length = int(self.bar_length * self.current / self.total) if self.total > 0 else 0
        bar = self.bar_format * filled_length + self.empty_format * (self.bar_length - filled_length)
        
        # Build display string
        display_parts = [f"\r{self.description}: [{bar}]"]
        
        if self.show_percentage:
            display_parts.append(f" {percentage:6.2f}%")
        
        if self.show_count:
            display_parts.append(f" {self.current}/{self.total}")
        
        # Calculate rate and ETA
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0 and self.current > 0:
            rate = self.current / elapsed_time
            
            if self.show_rate:
                display_parts.append(f" | Rate: {rate:.2f} items/sec")
            
            if self.show_eta and self.current < self.total:
                remaining_items = self.total - self.current
                eta_seconds = remaining_items / rate if rate > 0 else 0
                eta_formatted = self._format_time(eta_seconds)
                display_parts.append(f" | ETA: {eta_formatted}")
        
        # Write to output
        display_string = "".join(display_parts)
        self.file.write(display_string)
        self.file.flush()
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def close(self):
        """Close the progress bar and print a newline."""
        with self.lock:
            if not self._closed:
                self._display()
                self.file.write("\n")
                self.file.flush()
                self._closed = True
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class SimpleSpinner:
    """
    A simple spinner for indeterminate progress indication.
    
    Example usage:
        spinner = SimpleSpinner("Processing files...")
        spinner.start()
        # Do some work
        spinner.stop()
    """
    
    def __init__(self, description: str = "Working", 
                 spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
                 file=None):
        """
        Initialize the spinner.
        
        Args:
            description: Description text to display
            spinner_chars: Characters to cycle through for animation
            file: Output stream (default: sys.stdout)
        """
        self.description = description
        self.spinner_chars = spinner_chars
        self.file = file or sys.stdout
        self.current_char = 0
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
    
    def start(self):
        """Start the spinner animation."""
        with self.lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._spin, daemon=True)
                self.thread.start()
    
    def stop(self):
        """Stop the spinner animation."""
        with self.lock:
            if self.running:
                self.running = False
                if self.thread:
                    self.thread.join()
                # Clear the spinner line
                self.file.write(f"\r{' ' * (len(self.description) + 10)}\r")
                self.file.flush()
    
    def _spin(self):
        """Internal method to animate the spinner."""
        while self.running:
            char = self.spinner_chars[self.current_char % len(self.spinner_chars)]
            self.file.write(f"\r{char} {self.description}")
            self.file.flush()
            self.current_char += 1
            time.sleep(0.1)


class MultiFileProgress:
    """
    A progress tracker for processing multiple files.
    
    Example usage:
        files = ["file1.txt", "file2.txt", "file3.txt"]
        multi_progress = MultiFileProgress(files, "Analyzing logs")
        
        for file_path in files:
            multi_progress.start_file(file_path)
            # Process file with line-by-line progress
            with open(file_path) as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    # Process line
                    multi_progress.update_file_progress(i + 1, len(lines))
            multi_progress.complete_file()
    """
    
    def __init__(self, file_list: list, description: str = "Processing files"):
        """
        Initialize multi-file progress tracker.
        
        Args:
            file_list: List of files to process
            description: Description of the operation
        """
        self.file_list = file_list
        self.description = description
        self.total_files = len(file_list)
        self.current_file_index = 0
        self.current_file_name = ""
        self.overall_progress = ProgressBar(
            total=self.total_files,
            description=f"{description} - Overall",
            show_rate=False
        )
        self.file_progress = None
    
    def start_file(self, file_path: str, total_lines: Optional[int] = None):
        """
        Start processing a new file.
        
        Args:
            file_path: Path to the file being processed
            total_lines: Total number of lines in file (optional)
        """
        self.current_file_name = file_path
        
        if total_lines:
            self.file_progress = ProgressBar(
                total=total_lines,
                description=f"  ↳ {file_path}",
                bar_length=30,
                show_rate=False,
                show_eta=False
            )
    
    def update_file_progress(self, current_line: int, total_lines: int):
        """
        Update progress for the current file.
        
        Args:
            current_line: Current line being processed
            total_lines: Total lines in the file
        """
        if self.file_progress:
            self.file_progress.set_progress(current_line)
    
    def complete_file(self):
        """Mark the current file as complete."""
        if self.file_progress:
            self.file_progress.close()
            self.file_progress = None
        
        self.current_file_index += 1
        self.overall_progress.update(1)
    
    def close(self):
        """Close all progress bars."""
        if self.file_progress:
            self.file_progress.close()
        self.overall_progress.close()


# Convenience functions for quick usage
def progress_bar(iterable, description: str = "Progress", **kwargs):
    """
    Wrap an iterable with a progress bar.
    
    Args:
        iterable: The iterable to wrap
        description: Progress description
        **kwargs: Additional arguments for ProgressBar
    
    Returns:
        Generator that yields items with progress tracking
    """
    total = len(iterable) if hasattr(iterable, '__len__') else None
    if total is None:
        # For iterables without length, use a spinner
        spinner = SimpleSpinner(description)
        spinner.start()
        try:
            for item in iterable:
                yield item
        finally:
            spinner.stop()
    else:
        with ProgressBar(total=total, description=description, **kwargs) as pbar:
            for item in iterable:
                yield item
                pbar.update(1)


def count_lines_in_file(file_path: str) -> int:
    """
    Efficiently count lines in a file for progress bar initialization.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Number of lines in the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


if __name__ == "__main__":
    # Demo of the progress bar plugin
    import random
    
    print("Progress Bar Plugin Demo\n")
    
    # Demo 1: Basic progress bar
    print("Demo 1: Basic Progress Bar")
    with ProgressBar(total=50, description="Basic Demo") as pbar:
        for i in range(50):
            time.sleep(0.05)  # Simulate work
            pbar.update(1)
    
    print("\nDemo 2: Simple Spinner")
    spinner = SimpleSpinner("Loading data...")
    spinner.start()
    time.sleep(3)
    spinner.stop()
    print("Done!\n")
    
    # Demo 3: Multi-file processing
    print("Demo 3: Multi-file Processing")
    fake_files = [f"file_{i}.log" for i in range(5)]
    multi_progress = MultiFileProgress(fake_files, "Processing logs")
    
    for file_path in fake_files:
        lines = random.randint(50, 200)  # Simulate different file sizes
        multi_progress.start_file(file_path, lines)
        
        for line_num in range(lines):
            time.sleep(0.01)  # Simulate processing
            multi_progress.update_file_progress(line_num + 1, lines)
        
        multi_progress.complete_file()
    
    multi_progress.close()
    print("\nDemo complete!")