py pip45import argparse
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pandas as pd

try:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
except ImportError as error:
    raise SystemExit(
        "Missing dependency: matplotlib. Install with: pip install matplotlib pandas"
    ) from error


REQUIRED_COLUMNS = {"timestamp", "allocated_mem", "peak_allocation"}
EVENT_COLUMN = "cmdStatus_event"
UNEXPECTED_GAP_EVENT_COLUMN = "unexpected_gap_event"
CMD_EVENT_COLOR = "#ff7f0e"
UNEXPECTED_GAP_EVENT_COLOR = "#d62728"


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

    if EVENT_COLUMN not in df.columns:
        df[EVENT_COLUMN] = ""
    df[EVENT_COLUMN] = df[EVENT_COLUMN].fillna("").astype(str).str.strip()

    if UNEXPECTED_GAP_EVENT_COLUMN not in df.columns:
        df[UNEXPECTED_GAP_EVENT_COLUMN] = ""
    df[UNEXPECTED_GAP_EVENT_COLUMN] = (
        df[UNEXPECTED_GAP_EVENT_COLUMN].fillna("").astype(str).str.strip()
    )

    return df.sort_values("timestamp")


def compute_event_x_positions(
    event_timestamps: Sequence[pd.Timestamp],
    plot_timestamps: pd.Series,
    sample_index: List[int],
) -> List[float]:
    event_x_positions: List[float] = []
    first_x = float(sample_index[0])
    last_x = float(sample_index[-1])

    for event_timestamp in event_timestamps:
        insertion_index = plot_timestamps.searchsorted(event_timestamp, side="left")
        if insertion_index <= 0:
            event_x = first_x
        elif insertion_index >= len(plot_timestamps):
            event_x = last_x
        else:
            prev_timestamp = plot_timestamps.iloc[insertion_index - 1]
            next_timestamp = plot_timestamps.iloc[insertion_index]
            window_seconds = (next_timestamp - prev_timestamp).total_seconds()
            if window_seconds <= 0:
                fraction = 0.0
            else:
                fraction = (event_timestamp - prev_timestamp).total_seconds() / window_seconds
            event_x = float(sample_index[insertion_index - 1]) + fraction

        event_x_positions.append(event_x)

    return event_x_positions


def plot_csv_files(
    csv_files: List[Path],
    output: Path,
    start_index: Optional[int],
    end_index: Optional[int],
    show_plot: bool,
) -> None:
    total_rows = sum(count_data_rows(csv_file) for csv_file in csv_files)
    print(f"Total rows to process: {total_rows}", flush=True)

    if start_index is None and end_index is None:
        print("No index range provided; processing full file.", flush=True)
    else:
        print(
            f"Processing index range: start={start_index}, end={end_index}",
            flush=True,
        )

    fig, ax = plt.subplots(figsize=(14, 8))

    processed_rows = 0
    all_cmd_event_x: List[float] = []
    all_gap_event_x: List[float] = []

    for csv_file in csv_files:
        data = load_csv(csv_file)
        processed_rows += len(data)
        if total_rows > 0:
            progress = min(processed_rows / total_rows, 1.0)
            print(f"Progress: {processed_rows}/{total_rows} rows ({progress:.1%})", flush=True)
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

        sample_index = plot_data["sample_index"].tolist()
        source_name = csv_file.stem

        ax.plot(
            sample_index,
            plot_data["allocated_mem"],
            marker="o",
            markersize=2,
            linewidth=1.2,
            label=f"{source_name} - allocated_mem",
        )
        ax.plot(
            sample_index,
            plot_data["peak_allocation"],
            linestyle="--",
            marker="o",
            markersize=2,
            linewidth=1.2,
            label=f"{source_name} - peak_allocation",
        )

        plot_timestamps = plot_data["timestamp"].reset_index(drop=True)
        window_start = plot_timestamps.iloc[0]
        window_end = plot_timestamps.iloc[-1]

        cmd_event_rows = data[
            (data[EVENT_COLUMN].str.upper() == "X")
            & data["timestamp"].notna()
            & (data["timestamp"] >= window_start)
            & (data["timestamp"] <= window_end)
        ]
        gap_event_rows = data[
            (data[UNEXPECTED_GAP_EVENT_COLUMN].str.upper() == "X")
            & data["timestamp"].notna()
            & (data["timestamp"] >= window_start)
            & (data["timestamp"] <= window_end)
        ]

        all_cmd_event_x.extend(
            compute_event_x_positions(cmd_event_rows["timestamp"], plot_timestamps, sample_index)
        )
        all_gap_event_x.extend(
            compute_event_x_positions(gap_event_rows["timestamp"], plot_timestamps, sample_index)
        )

    y_min, y_max = ax.get_ylim()
    if all_cmd_event_x:
        ax.vlines(
            all_cmd_event_x,
            y_min,
            y_max,
            colors=CMD_EVENT_COLOR,
            linestyles=":",
            linewidth=0.8,
            alpha=0.6,
        )
    if all_gap_event_x:
        ax.vlines(
            all_gap_event_x,
            y_min,
            y_max,
            colors=UNEXPECTED_GAP_EVENT_COLOR,
            linestyles="--",
            linewidth=1.2,
            alpha=0.85,
        )

    event_legend: List[Line2D] = []
    if all_cmd_event_x:
        event_legend.append(
            Line2D([0], [0], color=CMD_EVENT_COLOR, linestyle=":", label=EVENT_COLUMN)
        )
    if all_gap_event_x:
        event_legend.append(
            Line2D(
                [0], [0], color=UNEXPECTED_GAP_EVENT_COLOR, linestyle="--", label=UNEXPECTED_GAP_EVENT_COLUMN
            )
        )

    handles, labels = ax.get_legend_handles_labels()
    if event_legend:
        handles.extend(event_legend)
        labels.extend([item.get_label() for item in event_legend])

    if handles:
        ax.legend(handles, labels, loc="best")

    ax.set_title("Heap Usage")
    ax.set_xlabel("Sample Index")
    ax.set_ylabel("Memory")
    ax.grid(True, alpha=0.3)

    print(f"Saving plot to: {output}", flush=True)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    print(f"Plot saved to: {output}", flush=True)

    if show_plot:
        plt.show()

    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Plot allocated_mem and peak_allocation using Matplotlib, with vertical "
            "markers for cmdStatus_event and unexpected_gap_event."
        )
    )
    parser.add_argument("csv_files", nargs="+", type=Path, help="One or more CSV files to plot")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("heap_usage_plot.png"),
        help="Output image file path (PNG/SVG/PDF based on extension)",
    )
    parser.add_argument("--show", action="store_true", help="Show interactive plot window")
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

    plot_csv_files(
        csv_files=csv_files,
        output=args.output.resolve(),
        start_index=args.start_index,
        end_index=args.end_index,
        show_plot=args.show,
    )


if __name__ == "__main__":
    main()
