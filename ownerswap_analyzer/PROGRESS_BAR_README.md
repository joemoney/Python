# Progress Bar Plugin

A comprehensive progress bar plugin for Python applications that provides visual feedback during long-running operations like file processing, data analysis, and batch operations.

## Features

- **Multiple Progress Types**: Basic progress bars, spinners, and multi-file progress tracking
- **Customizable Appearance**: Configurable bar length, characters, colors, and display options
- **Performance Metrics**: Shows percentage, count, processing rate, and estimated time to completion
- **Thread-Safe**: Can be safely used in multi-threaded applications
- **Memory Efficient**: Optimized for processing large datasets
- **Easy Integration**: Simple API that works with existing code

## Quick Start

### Basic Progress Bar

```python
from progress_bar import ProgressBar

# Basic usage
with ProgressBar(total=100, description="Processing") as pbar:
    for i in range(100):
        # Do some work
        pbar.update(1)
```

### Processing Files with Progress

```python
from progress_bar import ProgressBar, count_lines_in_file

def process_file(file_path):
    total_lines = count_lines_in_file(file_path)
    
    with ProgressBar(total=total_lines, description=f"Processing {file_path}") as pbar:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Process the line
                process_line(line)
                pbar.update(1)
```

### Multi-File Processing

```python
from progress_bar import MultiFileProgress

files = ["file1.txt", "file2.txt", "file3.txt"]
multi_progress = MultiFileProgress(files, "Analyzing files")

for file_path in files:
    lines = count_lines_in_file(file_path)
    multi_progress.start_file(file_path, lines)
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Process line
            multi_progress.update_file_progress(line_num, lines)
    
    multi_progress.complete_file()

multi_progress.close()
```

### Simple Spinner for Indeterminate Tasks

```python
from progress_bar import SimpleSpinner

spinner = SimpleSpinner("Loading data...")
spinner.start()
# Do some work that takes unknown time
spinner.stop()
```

## API Reference

### ProgressBar Class

The main progress bar class with extensive customization options.

```python
ProgressBar(
    total: int,                    # Total number of items to process
    description: str = "Progress", # Description text
    bar_length: int = 50,         # Length of progress bar in characters
    show_percentage: bool = True,  # Show percentage complete
    show_count: bool = True,      # Show current/total count
    show_rate: bool = True,       # Show processing rate
    show_eta: bool = True,        # Show estimated time to completion
    bar_format: str = "█",        # Character for completed portion
    empty_format: str = "░",      # Character for empty portion
    file = None                   # Output stream (default: sys.stdout)
)
```

**Methods:**
- `update(n=1)`: Advance progress by n steps
- `set_progress(value)`: Set progress to specific value
- `close()`: Close progress bar and print newline

### SimpleSpinner Class

For tasks with unknown duration or indeterminate progress.

```python
SimpleSpinner(
    description: str = "Working",           # Description text
    spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", # Animation characters
    file = None                            # Output stream
)
```

**Methods:**
- `start()`: Start spinner animation
- `stop()`: Stop spinner and clear display

### MultiFileProgress Class

For tracking progress across multiple files.

```python
MultiFileProgress(
    file_list: list,                    # List of files to process
    description: str = "Processing files" # Operation description
)
```

**Methods:**
- `start_file(file_path, total_lines=None)`: Begin processing a file
- `update_file_progress(current_line, total_lines)`: Update file progress
- `complete_file()`: Mark current file as complete
- `close()`: Close all progress displays

### Utility Functions

- `progress_bar(iterable, description, **kwargs)`: Wrap iterable with progress
- `count_lines_in_file(file_path)`: Efficiently count lines in a file

## Integration Examples

### With Your Existing Log Analyzer

The progress bar has been integrated into your `ownerswap_analyzer.py`. It now shows:
- Overall progress across all log files
- Individual file progress as each file is processed
- Processing rate and estimated completion time

### Custom Styling

```python
# Create a custom-styled progress bar
with ProgressBar(
    total=100,
    description="Custom Progress",
    bar_format="▓",        # Solid block
    empty_format="▒",      # Light shade
    bar_length=60,         # Longer bar
    show_rate=False        # Hide processing rate
) as pbar:
    # Your processing code here
    pass
```

## Best Practices

1. **Always use context managers** (`with` statements) to ensure proper cleanup
2. **Count lines beforehand** for file processing to show accurate progress
3. **Update progress in reasonable intervals** (not every microsecond)
4. **Use spinners for indeterminate tasks** like network operations
5. **Choose appropriate descriptions** that help users understand what's happening

## Error Handling

The progress bar handles common scenarios gracefully:
- Files that can't be read (shows 0 lines)
- Interrupted operations (proper cleanup)
- Thread safety for concurrent operations
- Automatic bounds checking (progress can't exceed total)

## Performance Notes

- Progress updates are throttled to prevent excessive screen updates
- Line counting is optimized for large files
- Memory usage remains constant regardless of file size
- Thread locks are minimal to avoid blocking main operations

## Dependencies

- Standard library only (no external dependencies required)
- Compatible with Python 3.6+
- Works on Windows, macOS, and Linux

## Running the Examples

```bash
# Run the integrated analyzer with progress bars
python ownerswap_analyzer.py

# Run standalone examples to see all features
python progress_examples.py
```

## Troubleshooting

**Progress bar not updating smoothly:**
- Updates are throttled to every 0.1 seconds for performance
- This is normal behavior for very fast operations

**Unicode characters not displaying:**
- Use ASCII characters in bar_format and empty_format if your terminal doesn't support Unicode
- Example: `bar_format="=", empty_format="-"`

**Progress bar interfering with other output:**
- Use a different file parameter to redirect output
- Ensure you're calling `close()` or using context managers