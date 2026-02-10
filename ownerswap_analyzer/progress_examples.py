"""
Example script demonstrating how to use the progress bar plugin
in different scenarios common to data processing and file analysis.
"""

import time
import random
from progress_bar import ProgressBar, SimpleSpinner, MultiFileProgress, progress_bar


def example_basic_progress():
    """Demonstrate basic progress bar usage."""
    print("Example 1: Basic Progress Bar")
    print("Processing 100 items...")
    
    with ProgressBar(total=100, description="Processing items") as pbar:
        for i in range(100):
            # Simulate some work
            time.sleep(0.02)
            pbar.update(1)
    print("✓ Complete!\n")


def example_file_processing():
    """Demonstrate file processing with progress tracking."""
    print("Example 2: File Processing Simulation")
    
    # Simulate processing a large file
    simulated_lines = 1000
    
    with ProgressBar(
        total=simulated_lines, 
        description="Analyzing log file",
        show_rate=True,
        show_eta=True
    ) as pbar:
        for line_num in range(simulated_lines):
            # Simulate reading and processing a line
            time.sleep(0.001)  # Very fast processing
            
            # Randomly simulate finding important events
            if random.random() < 0.05:  # 5% chance
                # Simulate more processing time for important lines
                time.sleep(0.01)
            
            pbar.update(1)
    print("✓ File analysis complete!\n")


def example_spinner():
    """Demonstrate spinner for indeterminate progress."""
    print("Example 3: Spinner for Indeterminate Tasks")
    
    spinner = SimpleSpinner("Connecting to server...")
    spinner.start()
    time.sleep(2)  # Simulate connection time
    spinner.stop()
    print("✓ Connected successfully!")
    
    spinner = SimpleSpinner("Downloading configuration...")
    spinner.start()
    time.sleep(1.5)
    spinner.stop()
    print("✓ Configuration downloaded!\n")


def example_multi_file():
    """Demonstrate multi-file processing."""
    print("Example 4: Multi-file Processing")
    
    # Simulate multiple files with different sizes
    fake_files = [
        ("system.log", 500),
        ("error.log", 200),
        ("debug.log", 800),
        ("access.log", 1200)
    ]
    
    file_names = [f[0] for f in fake_files]
    multi_progress = MultiFileProgress(file_names, "Processing log files")
    
    for file_name, line_count in fake_files:
        multi_progress.start_file(file_name, line_count)
        
        # Simulate processing each line
        for line_num in range(line_count):
            # Vary processing speed
            time.sleep(random.uniform(0.001, 0.005))
            multi_progress.update_file_progress(line_num + 1, line_count)
        
        multi_progress.complete_file()
    
    multi_progress.close()
    print("✓ All files processed!\n")


def example_iterable_wrapper():
    """Demonstrate wrapping iterables with progress."""
    print("Example 5: Wrapping Iterables")
    
    # Create some sample data
    data_list = list(range(50))
    
    # Process with automatic progress tracking
    results = []
    for item in progress_bar(data_list, "Processing data"):
        # Simulate processing
        time.sleep(0.05)
        results.append(item * 2)
    
    print(f"✓ Processed {len(results)} items!\n")


def example_custom_styling():
    """Demonstrate custom progress bar styling."""
    print("Example 6: Custom Styling")
    
    # Custom styled progress bar
    with ProgressBar(
        total=30,
        description="Custom Style",
        bar_format="▓",  # Different fill character
        empty_format="▒",  # Different empty character
        bar_length=40,   # Longer bar
        show_percentage=True,
        show_count=True,
        show_rate=False,  # Hide rate
        show_eta=False    # Hide ETA
    ) as pbar:
        for i in range(30):
            time.sleep(0.1)
            pbar.update(1)
    print("✓ Custom styling complete!\n")


def main():
    """Run all examples."""
    print("Progress Bar Plugin Examples")
    print("=" * 40)
    print()
    
    try:
        example_basic_progress()
        example_file_processing()
        example_spinner()
        example_multi_file()
        example_iterable_wrapper()
        example_custom_styling()
        
        print("All examples completed successfully!")
        print("\nYou can now use these patterns in your own code:")
        print("1. Import: from progress_bar import ProgressBar, SimpleSpinner, MultiFileProgress")
        print("2. Choose the appropriate progress type for your task")
        print("3. Wrap your loops or long-running operations")
        print("4. Enjoy better user experience with progress feedback!")
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
    except Exception as e:
        print(f"\nError running examples: {e}")


if __name__ == "__main__":
    main()