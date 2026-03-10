import argparse
import csv
import re
from pathlib import Path
from typing import Optional


HEAP_LINE_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\].*?Allocated Mem:\s*(?P<allocated>\d+),\s*Peak Allocation:\s*(?P<peak>\d+)",
)
CMD_STATUS_EVENT_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\].*?BLE Stack Event:\s*91\s*Status:\s*0f",
    re.IGNORECASE,
)
UNEXPECTED_GAP_EVENT_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\].*?BLE Stack Event:\s*d0\s*Status:\s*30",
    re.IGNORECASE,
)
L2CAP_CLOSED_EVENT_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\].*?L2CAP Requested Disconenct",
    re.IGNORECASE,
)


def parse_heap_log(input_file: Path, event_column: Optional[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    with input_file.open("r", encoding="utf-8", errors="replace") as file:
        for line in file:
            heap_match = HEAP_LINE_PATTERN.search(line)
            if heap_match:
                row = {
                    "timestamp": heap_match.group("timestamp"),
                    "allocated_mem": heap_match.group("allocated"),
                    "peak_allocation": heap_match.group("peak"),
                }
                if event_column is not None:
                    row[event_column] = ""
                rows.append(row)
                continue

            cmd_status_event_match = CMD_STATUS_EVENT_PATTERN.search(line)
            if cmd_status_event_match and event_column == "cmdStatus_event":
                rows.append(
                    {
                        "timestamp": cmd_status_event_match.group("timestamp"),
                        "allocated_mem": "",
                        "peak_allocation": "",
                        event_column: "X",
                    }
                )
                continue

            unexpected_gap_event_match = UNEXPECTED_GAP_EVENT_PATTERN.search(line)
            if (
                unexpected_gap_event_match
                and event_column == "unexpected_gap_event"
            ):
                rows.append(
                    {
                        "timestamp": unexpected_gap_event_match.group("timestamp"),
                        "allocated_mem": "",
                        "peak_allocation": "",
                        event_column: "X",
                    }
                )
                continue

            l2cap_closed_event_match = L2CAP_CLOSED_EVENT_PATTERN.search(line)
            if l2cap_closed_event_match and event_column == "l2cap_closed":
                rows.append(
                    {
                        "timestamp": l2cap_closed_event_match.group("timestamp"),
                        "allocated_mem": "",
                        "peak_allocation": "",
                        event_column: "X",
                    }
                )

    return rows


def write_csv(output_file: Path, rows: list[dict[str, str]], event_column: Optional[str]) -> None:
    with output_file.open("w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "timestamp",
            "allocated_mem",
            "peak_allocation",
        ]
        if event_column is not None:
            fieldnames.append(event_column)

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Parse log lines containing 'Allocated Mem' and "
            "'BLE Stack Event: 91 Status: 0f', 'BLE Stack Event: d0 Status: 30', "
            "and 'L2CAP Requested Disconnect', "
            "then export timestamp, allocated_mem, peak_allocation, "
            "and the selected event column to CSV."
        )
    )
    parser.add_argument("input_log", type=Path, help="Path to the input log file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output CSV file path (default: <input_name>_heap.csv)",
    )
    parser.add_argument(
        "--capture-event",
        dest="capture_event",
        choices=["cmdStatus_event", "unexpected_gap_event", "l2cap_closed"],
        default=None,
        help=(
            "Select one event type to capture in the CSV. "
            "If omitted, no event column is captured. "
            "Allowed values: cmdStatus_event, unexpected_gap_event, l2cap_closed"
        ),
    )

    args = parser.parse_args()

    input_log: Path = args.input_log
    if not input_log.exists() or not input_log.is_file():
        raise FileNotFoundError(f"Input log file not found: {input_log}")

    output_csv = args.output
    if output_csv is None:
        output_csv = input_log.with_name(f"{input_log.stem}_heap.csv")

    rows = parse_heap_log(input_log, args.capture_event)
    write_csv(output_csv, rows, args.capture_event)

    print(f"Wrote {len(rows)} rows to {output_csv}")


if __name__ == "__main__":
    main()