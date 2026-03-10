import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

ALLOCATED_MEM_RE = re.compile(r"Allocated\s+Mem:\s*(\d+)", re.IGNORECASE)
TIMESTAMP_RE = re.compile(r"^\[(.*?)\]")


@dataclass
class MemPoint:
    line_number: int
    value: int
    timestamp: Optional[str]
    raw_line: str


@dataclass
class IncreaseEvent:
    previous: MemPoint
    current: MemPoint
    delta: int


@dataclass
class DecreaseEvent:
    previous: MemPoint
    current: MemPoint
    delta: int


@dataclass
class IncreaseReversionEvent:
    increase: IncreaseEvent
    reverted_at: MemPoint
    delta: int


def extract_allocated_mem(line: str) -> Optional[int]:
    match = ALLOCATED_MEM_RE.search(line)
    if not match:
        return None
    return int(match.group(1))


def extract_timestamp(line: str) -> Optional[str]:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return None
    return match.group(1)


def format_point(point: MemPoint) -> str:
    if point.timestamp:
        return f"line {point.line_number}, ts {point.timestamp}, value {point.value}"
    return f"line {point.line_number}, value {point.value}"


def analyze_file(
    input_path: Path,
    output_path: Path,
    progress_lines: int = 200000,
    min_drop_mode: str = "latest",
) -> None:
    total_lines = 0
    matched_lines = 0

    global_min: Optional[MemPoint] = None
    global_max: Optional[MemPoint] = None

    prev_point: Optional[MemPoint] = None
    prev_trend = 0

    local_mins: List[MemPoint] = []
    local_maxs: List[MemPoint] = []

    min_increase_events: List[IncreaseEvent] = []
    min_increase_reversion_events: List[IncreaseReversionEvent] = []
    max_increase_events: List[IncreaseEvent] = []
    min_floor_point: Optional[MemPoint] = None
    max_ceiling_point: Optional[MemPoint] = None

    with input_path.open("r", encoding="utf-8", errors="replace") as log_file:
        for line_number, raw_line in enumerate(log_file, start=1):
            total_lines += 1
            value = extract_allocated_mem(raw_line)
            if value is None:
                if progress_lines > 0 and total_lines % progress_lines == 0:
                    print(f"Progress: scanned {total_lines:,} lines, matched {matched_lines:,} Allocated Mem lines")
                continue

            matched_lines += 1
            current = MemPoint(
                line_number=line_number,
                value=value,
                timestamp=extract_timestamp(raw_line),
                raw_line=raw_line.rstrip("\n"),
            )

            if global_min is None or value < global_min.value:
                global_min = current
            if global_max is None or value > global_max.value:
                global_max = current

            if prev_point is not None:
                if current.value > prev_point.value:
                    current_trend = 1
                elif current.value < prev_point.value:
                    current_trend = -1
                else:
                    current_trend = prev_trend

                if prev_trend > 0 and current_trend < 0:
                    local_max = prev_point
                    local_maxs.append(local_max)
                    if max_ceiling_point is None:
                        max_ceiling_point = local_max
                    elif local_max.value > max_ceiling_point.value:
                        max_increase_events.append(
                            IncreaseEvent(
                                previous=max_ceiling_point,
                                current=local_max,
                                delta=local_max.value - max_ceiling_point.value,
                            )
                        )
                        max_ceiling_point = local_max

                if prev_trend < 0 and current_trend > 0:
                    local_min = prev_point
                    local_mins.append(local_min)
                    if min_floor_point is None:
                        min_floor_point = local_min
                    elif local_min.value > min_floor_point.value:
                        min_increase_event = IncreaseEvent(
                                previous=min_floor_point,
                                current=local_min,
                                delta=local_min.value - min_floor_point.value,
                            )
                        min_increase_events.append(min_increase_event)
                        min_floor_point = local_min

                prev_trend = current_trend

            prev_point = current

            if progress_lines > 0 and total_lines % progress_lines == 0:
                print(f"Progress: scanned {total_lines:,} lines, matched {matched_lines:,} Allocated Mem lines")

    for increase_event in min_increase_events:
        reversion_point: Optional[MemPoint] = None
        for local_min in local_mins:
            if local_min.line_number <= increase_event.current.line_number:
                continue
            if local_min.value <= increase_event.previous.value:
                reversion_point = local_min
                if min_drop_mode == "first":
                    break

        if reversion_point is not None:
            min_increase_reversion_events.append(
                IncreaseReversionEvent(
                    increase=increase_event,
                    reverted_at=reversion_point,
                    delta=increase_event.current.value - reversion_point.value,
                )
            )

    with output_path.open("w", encoding="utf-8") as out:
        out.write("Allocated Mem analysis report\n")
        out.write(f"Input file: {input_path}\n")
        out.write(f"Total lines scanned: {total_lines:,}\n")
        out.write(f"Allocated Mem lines found: {matched_lines:,}\n")

        if global_min is None or global_max is None:
            out.write("No 'Allocated Mem:' entries found.\n")
        else:
            out.write(f"Global minimum Allocated Mem: {format_point(global_min)}\n")
            out.write(f"Global maximum Allocated Mem: {format_point(global_max)}\n")
            out.write("\n")

            out.write(f"Local minimum increases found: {len(min_increase_events)}\n")
            for event in min_increase_events:
                out.write(
                    f"MIN_INCREASE: {format_point(event.previous)} -> "
                    f"{format_point(event.current)}, delta=+{event.delta}\n"
                )

            out.write("\n")
            out.write(
                f"Minimum increase {min_drop_mode} reversions found: "
                f"{len(min_increase_reversion_events)}\n"
            )
            for event in min_increase_reversion_events:
                out.write(
                    f"MIN_DROP: increase {format_point(event.increase.previous)} -> "
                    f"{format_point(event.increase.current)} reverted at "
                    f"{format_point(event.reverted_at)}, delta=-{event.delta}\n"
                )

            out.write("\n")
            out.write(f"Local maximum increases found: {len(max_increase_events)}\n")
            for event in max_increase_events:
                out.write(
                    f"MAX_INCREASE: {format_point(event.previous)} -> "
                    f"{format_point(event.current)}, delta=+{event.delta}\n"
                )

    print("Analysis complete")
    print(f"Input: {input_path}")
    print(f"Scanned lines: {total_lines:,}")
    print(f"Allocated Mem matches: {matched_lines:,}")

    if global_min is None or global_max is None:
        print("No Allocated Mem entries found.")
    else:
        print(f"Global min: {global_min.value} at line {global_min.line_number}")
        print(f"Global max: {global_max.value} at line {global_max.line_number}")
        print(f"Local min increases: {len(min_increase_events)}")
        print(f"Min increase reversions: {len(min_increase_reversion_events)}")
        print(f"Local max increases: {len(max_increase_events)}")

    print(f"Report: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze log lines containing 'Allocated Mem:' and mark where local minima and "
            "local maxima increase over time."
        )
    )
    parser.add_argument("input_file", type=Path, help="Path to log file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("allocated_mem_report.txt"),
        help="Path to output report file",
    )
    parser.add_argument(
        "--progress-lines",
        type=int,
        default=200000,
        help="Print progress every N scanned lines (set 0 to disable)",
    )
    parser.add_argument(
        "--min-drop-mode",
        choices=["latest", "first"],
        default="latest",
        help=(
            "How to report MIN_DROP reversion point for each MIN_INCREASE: "
            "'latest' uses the last matching reversion, 'first' uses the first."
        ),
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        raise FileNotFoundError(f"Input file not found: {args.input_file}")

    analyze_file(args.input_file, args.output, args.progress_lines, args.min_drop_mode)


if __name__ == "__main__":
    main()
