import argparse
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional

import pandas as pd
from plotly.colors import qualitative

try:
    import plotly.graph_objects as go
except ImportError as error:
    raise SystemExit(
        "Missing dependency: plotly. Install with: pip install plotly pandas"
    ) from error


REQUIRED_COLUMNS = {"timestamp", "allocated_mem", "peak_allocation"}


def get_event_columns(df: pd.DataFrame) -> List[str]:
    return [
        column
        for column in df.columns
        if column not in REQUIRED_COLUMNS
    ]


@contextmanager
def progress_heartbeat(label: str, interval_seconds: float = 5.0) -> Iterator[None]:
    stop_event = threading.Event()
    start_time = time.time()

    def _heartbeat() -> None:
        while not stop_event.wait(interval_seconds):
            elapsed = time.time() - start_time
            print(f"{label} in progress... {elapsed:.1f}s elapsed", flush=True)

    thread = threading.Thread(target=_heartbeat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop_event.set()
        thread.join(timeout=interval_seconds + 1.0)
        elapsed = time.time() - start_time
        print(f"{label} completed in {elapsed:.1f}s", flush=True)


def count_data_rows(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", errors="replace") as file:
        line_count = sum(1 for _ in file)
    return max(0, line_count - 1)


def load_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"{csv_path} is missing required columns: {missing_list}")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["allocated_mem"] = pd.to_numeric(df["allocated_mem"], errors="coerce")
    df["peak_allocation"] = pd.to_numeric(df["peak_allocation"], errors="coerce")

    for event_column in get_event_columns(df):
        df[event_column] = df[event_column].fillna("").astype(str).str.strip()

    return df.sort_values("timestamp")


def build_figure(
    csv_files: List[Path],
    start_index: Optional[int] = None,
    end_index: Optional[int] = None,
    total_rows: Optional[int] = None,
) -> go.Figure:
    fig = go.Figure()
    color_palette = qualitative.Plotly
    event_palette = qualitative.Dark24
    processed_rows = 0

    for index, csv_file in enumerate(csv_files):
        data = load_csv(csv_file)
        processed_rows += len(data)
        if total_rows and total_rows > 0:
            progress = min(processed_rows / total_rows, 1.0)
            print(
                f"Progress: {processed_rows}/{total_rows} rows ({progress:.1%})",
                flush=True,
            )
        else:
            print(f"Progress: {processed_rows} rows processed", flush=True)

        plot_data = data.dropna(subset=["timestamp", "allocated_mem", "peak_allocation"])
        if plot_data.empty:
            continue

        plot_data = plot_data.reset_index(drop=True).copy()
        plot_data["sample_index"] = range(1, len(plot_data) + 1)
        if start_index is not None:
            plot_data = plot_data[plot_data["sample_index"] >= start_index]
        if end_index is not None:
            plot_data = plot_data[plot_data["sample_index"] <= end_index]
        if plot_data.empty:
            continue

        source_name = csv_file.stem
        base_color = color_palette[index % len(color_palette)]
        sample_index = plot_data["sample_index"].tolist()
        hover_text = plot_data["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str[:-3]

        fig.add_trace(
            go.Scatter(
                x=sample_index,
                y=plot_data["allocated_mem"],
                mode="lines+markers",
                name=f"{source_name} - allocated_mem",
                line={"color": base_color},
                marker={"color": base_color},
                customdata=hover_text,
                hovertemplate=(
                    "Sample: %{x}<br>"
                    "Allocated: %{y}<br>"
                    "Timestamp: %{customdata}<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=sample_index,
                y=plot_data["peak_allocation"],
                mode="lines+markers",
                name=f"{source_name} - peak_allocation",
                line={"dash": "dash", "color": base_color},
                marker={"color": base_color},
                customdata=hover_text,
                hovertemplate=(
                    "Sample: %{x}<br>"
                    "Peak: %{y}<br>"
                    "Timestamp: %{customdata}<extra></extra>"
                ),
            )
        )

        event_columns = get_event_columns(data)

        plot_timestamps = plot_data["timestamp"].reset_index(drop=True)
        window_start = plot_timestamps.iloc[0]
        window_end = plot_timestamps.iloc[-1]
        first_x = float(sample_index[0])
        last_x = float(sample_index[-1])

        for event_index, event_column in enumerate(event_columns):
            event_rows = data[
                (data[event_column].str.upper() == "X") & data["timestamp"].notna()
            ]
            event_rows = event_rows[
                (event_rows["timestamp"] >= window_start)
                & (event_rows["timestamp"] <= window_end)
            ]
            event_color = event_palette[event_index % len(event_palette)]

            for event_timestamp in event_rows["timestamp"]:
                insertion_index = plot_timestamps.searchsorted(event_timestamp, side="left")
                if insertion_index <= 0:
                    event_x = first_x
                elif insertion_index >= len(plot_timestamps):
                    event_x = last_x
                else:
                    prev_timestamp = plot_timestamps.iloc[insertion_index - 1]
                    next_timestamp = plot_timestamps.iloc[insertion_index]
                    window = (next_timestamp - prev_timestamp).total_seconds()
                    if window <= 0:
                        fraction = 0.0
                    else:
                        fraction = (
                            event_timestamp - prev_timestamp
                        ).total_seconds() / window
                    event_x = float(sample_index[insertion_index - 1]) + fraction

                fig.add_vline(
                    x=event_x,
                    line_width=2,
                    line_dash="dot",
                    line_color=event_color,
                    opacity=0.85,
                    annotation_text=event_column,
                    annotation_position="top",
                )

    fig.update_layout(
        title="Heap Usage",
        xaxis_title="Sample Index",
        yaxis_title="Memory",
        hovermode="x unified",
        template="plotly_white",
    )
    fig.update_xaxes(type="linear", rangeslider_visible=True)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Plot allocated_mem and peak_allocation from one or more CSV files "
            "into an interactive zoomable chart, and draw vertical lines for "
            "any event columns (non-heap columns) with rows marked 'X'."
        )
    )
    parser.add_argument(
        "csv_files",
        nargs="+",
        type=Path,
        help="One or more CSV files to plot",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("heap_usage_plot.html"),
        help="Output HTML file path",
    )
    parser.add_argument(
        "--auto-open",
        action="store_true",
        help="Automatically open the HTML file in your browser",
    )
    parser.add_argument(
        "--start-index",
        "--start_index",
        dest="start_index",
        type=int,
        default=None,
        help="Start sample index (1-based, inclusive)",
    )
    parser.add_argument(
        "--end-index",
        "--end_index",
        dest="end_index",
        type=int,
        default=None,
        help="End sample index (1-based, inclusive)",
    )

    args = parser.parse_args()

    csv_files = [path.resolve() for path in args.csv_files]
    for csv_file in csv_files:
        if not csv_file.exists() or not csv_file.is_file():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

    if args.start_index is not None and args.start_index < 1:
        raise ValueError("--start-index must be >= 1")
    if args.end_index is not None and args.end_index < 1:
        raise ValueError("--end-index must be >= 1")
    if (
        args.start_index is not None
        and args.end_index is not None
        and args.end_index < args.start_index
    ):
        raise ValueError("--end-index must be >= --start-index")

    if args.start_index is None and args.end_index is None:
        print("No index range provided; processing full file.", flush=True)
    else:
        print(
            f"Processing index range: start={args.start_index}, end={args.end_index}",
            flush=True,
        )

    total_rows = sum(count_data_rows(csv_file) for csv_file in csv_files)
    print(f"Total rows to process: {total_rows}", flush=True)

    print("Starting figure build...", flush=True)
    with progress_heartbeat("Figure build"):
        fig = build_figure(csv_files, args.start_index, args.end_index, total_rows)

    output = args.output.resolve()
    print(f"Starting HTML export: {output}", flush=True)
    with progress_heartbeat("HTML export"):
        fig.write_html(str(output), auto_open=args.auto_open)

    print(f"Interactive plot saved to: {output}")


if __name__ == "__main__":
    main()