import argparse
import os
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

MALLOC_PATTERNS = (
    ("icall_malloc", re.compile(r"ICall_malloc\s+size\s+(\d+)\s*,\s*add\s+([0-9A-Fa-fx]+)", re.IGNORECASE)),
    ("ipc_tx_malloc", re.compile(r"IPC\s+Tx\s+Malloc\s*:\s*([0-9A-Fa-fx]+)\s*,\s*size\s*:\s*(\d+)", re.IGNORECASE)),
    ("ipc_rx_malloc", re.compile(r"IPC\s+Rx\s+Malloc\s*:\s*([0-9A-Fa-fx]+)\s*,\s*size\s*:\s*(\d+)", re.IGNORECASE)),
)

FREE_PATTERNS = (
    ("icall_free", re.compile(r"ICall_free\s+msg\s+([0-9A-Fa-fx]+)", re.IGNORECASE)),
    ("icall_freemsg", re.compile(r"ICall_freeMsg\s+msg\s+([0-9A-Fa-fx]+)", re.IGNORECASE)),
    ("ipc_rx_free", re.compile(r"IPC\s+Rx\s+Free\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)),
    ("spi_callback_free", re.compile(r"SPI\s+Callback\s+Free\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)),
)


@dataclass
class AllocationEvent:
    line: int
    size: int
    event_type: str
    raw: str


def normalize_addr(addr: str) -> str:
    value = addr.strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value


def parse_event_from_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    for event_type, pattern in MALLOC_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue

        if event_type == "icall_malloc":
            size = int(match.group(1))
            addr = normalize_addr(match.group(2))
        else:
            addr = normalize_addr(match.group(1))
            size = int(match.group(2))

        return event_type, addr, size

    for event_type, pattern in FREE_PATTERNS:
        match = pattern.search(line)
        if match:
            return event_type, normalize_addr(match.group(1)), None

    return None, None, None

def analyze(
    log_path: str,
    output_path: str,
    progress_interval_mb: int = 25,
    match_order: str = "lifo",
    suspected_free_mode: str = "apply",
) -> None:
    file_size = os.path.getsize(log_path)
    progress_interval_bytes = max(1, progress_interval_mb * 1024 * 1024)
    next_progress_mark = progress_interval_bytes

    open_allocations: Dict[str, Deque[AllocationEvent]] = defaultdict(deque)
    unmatched_frees: List[Tuple[int, str, str, str]] = []
    suspected_frees: List[Tuple[int, str, int, str, str]] = []

    malloc_count = 0
    free_count = 0
    matched_count = 0
    ignored_lines = 0
    processed_lines = 0
    bytes_read = 0

    malloc_type_counts = Counter()
    free_type_counts = Counter()

    with open(log_path, "r", encoding="utf-8", errors="ignore") as log_file:
        for raw_line in log_file:
            processed_lines += 1
            bytes_read += len(raw_line.encode("utf-8", errors="ignore"))
            line = raw_line.rstrip("\n")

            event_type, addr, size = parse_event_from_line(line)
            if event_type is None:
                ignored_lines += 1
            elif size is not None:
                malloc_count += 1
                malloc_type_counts[event_type] += 1

                if open_allocations[addr] and suspected_free_mode != "off":
                    if match_order == "fifo":
                        inferred_freed = open_allocations[addr][0]
                    else:
                        inferred_freed = open_allocations[addr][-1]

                    suspected_frees.append(
                        (
                            inferred_freed.line,
                            addr,
                            processed_lines,
                            inferred_freed.raw,
                            line,
                        )
                    )

                    if suspected_free_mode == "apply":
                        if match_order == "fifo":
                            open_allocations[addr].popleft()
                        else:
                            open_allocations[addr].pop()

                open_allocations[addr].append(AllocationEvent(processed_lines, size, event_type, line))
            else:
                free_count += 1
                free_type_counts[event_type] += 1
                if open_allocations[addr]:
                    if match_order == "fifo":
                        open_allocations[addr].popleft()
                    else:
                        open_allocations[addr].pop()
                    matched_count += 1
                    if not open_allocations[addr]:
                        del open_allocations[addr]
                else:
                    unmatched_frees.append((processed_lines, event_type, addr, line))

            if bytes_read >= next_progress_mark or bytes_read == file_size:
                percent = (bytes_read / file_size * 100.0) if file_size else 100.0
                print(
                    f"Progress: {percent:6.2f}% | lines={processed_lines:,} | "
                    f"malloc={malloc_count:,} free={free_count:,} matched={matched_count:,}"
                )
                while next_progress_mark <= bytes_read:
                    next_progress_mark += progress_interval_bytes

    unmatched_mallocs: List[Tuple[int, str, int, str, str]] = []
    for addr, events in open_allocations.items():
        for event in events:
            unmatched_mallocs.append((event.line, addr, event.size, event.event_type, event.raw))

    unmatched_mallocs.sort(key=lambda x: x[0])
    unmatched_frees.sort(key=lambda x: x[0])
    unmatched_malloc_total_bytes = sum(size for _, _, size, _, _ in unmatched_mallocs)

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("ICall/IPC allocation-deallocation mismatch report (raw BLE UART)\n")
        out.write(f"Input file: {log_path}\n")
        out.write(f"Match order: {match_order}\n")
        out.write(f"Suspected free mode: {suspected_free_mode}\n")
        out.write(f"Processed lines: {processed_lines:,}\n")
        out.write(f"Matched pairs: {matched_count:,}\n")
        out.write(f"Unmatched mallocs: {len(unmatched_mallocs):,}\n")
        out.write(f"Unmatched malloc total bytes: {unmatched_malloc_total_bytes:,}\n")
        out.write(f"Unmatched frees: {len(unmatched_frees):,}\n")
        out.write(f"Suspected frees inferred by re-malloc: {len(suspected_frees):,}\n")
        out.write(f"Ignored lines: {ignored_lines:,}\n")
        out.write("\n")

        out.write("=== Event type counts ===\n")
        out.write("Malloc event types:\n")
        if malloc_type_counts:
            for event_type, count in sorted(malloc_type_counts.items()):
                out.write(f"  {event_type}: {count:,}\n")
        else:
            out.write("  None\n")

        out.write("Free event types:\n")
        if free_type_counts:
            for event_type, count in sorted(free_type_counts.items()):
                out.write(f"  {event_type}: {count:,}\n")
        else:
            out.write("  None\n")

        out.write("\n=== Unmatched malloc allocations (not freed) ===\n")
        if unmatched_mallocs:
            for line_num, addr, size, event_type, raw in unmatched_mallocs:
                out.write(
                    f"line={line_num}, type={event_type}, addr=0x{addr}, size={size}, event={raw}\n"
                )
        else:
            out.write("None\n")

        out.write("\n=== Unmatched deallocations (free without prior malloc) ===\n")
        if unmatched_frees:
            for line_num, event_type, addr, raw in unmatched_frees:
                out.write(
                    f"line={line_num}, type={event_type}, addr=0x{addr}, event={raw}\n"
                )
        else:
            out.write("None\n")

        out.write("\n=== Suspected frees inferred by same-address re-malloc ===\n")
        if suspected_frees:
            for suspected_line, addr, remalloc_line, suspected_event, remalloc_event in suspected_frees:
                out.write(
                    f"suspected_freed_line={suspected_line}, addr=0x{addr}, "
                    f"re_malloc_line={remalloc_line}\n"
                )
                out.write(f"  suspected_event={suspected_event}\n")
                out.write(f"  re_malloc_event={remalloc_event}\n")
        else:
            out.write("None\n")

    print("\nAnalysis complete")
    print(f"Lines processed: {processed_lines:,}")
    print(f"Matched pairs: {matched_count:,}")
    print(f"Unmatched mallocs: {len(unmatched_mallocs):,}")
    print(f"Unmatched malloc total bytes: {unmatched_malloc_total_bytes:,}")
    print(f"Unmatched frees: {len(unmatched_frees):,}")
    print(f"Suspected frees inferred by re-malloc: {len(suspected_frees):,}")
    print(f"Ignored lines: {ignored_lines:,}")
    print(f"Report written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze raw BLE UART logs and match ICall/IPC malloc allocations with free events."
        )
    )
    parser.add_argument("log_file", help="Path to raw BLE UART text log")
    parser.add_argument(
        "-o",
        "--output",
        default="icall_uart_mismatch_report.txt",
        help="Path to output text report (default: icall_uart_mismatch_report.txt)",
    )
    parser.add_argument(
        "--progress-mb",
        type=int,
        default=25,
        help="Print progress every N MB read (default: 25)",
    )
    parser.add_argument(
        "--match-order",
        choices=["fifo", "lifo"],
        default="lifo",
        help=(
            "Order used when matching frees to outstanding mallocs on the same "
            "address (default: lifo)."
        ),
    )
    parser.add_argument(
        "--suspected-free-mode",
        choices=["off", "report-only", "apply"],
        default="apply",
        help=(
            "How to handle same-address re-malloc inference: off (disable), "
            "report-only (report suspected frees but do not affect matching), "
            "apply (report and apply inferred free to matching state). "
            "Default: apply."
        ),
    )

    args = parser.parse_args()

    if not os.path.exists(args.log_file):
        raise FileNotFoundError(f"Input log not found: {args.log_file}")
    if args.progress_mb <= 0:
        raise ValueError("--progress-mb must be a positive integer")

    analyze(
        args.log_file,
        args.output,
        args.progress_mb,
        args.match_order,
        args.suspected_free_mode,
    )


if __name__ == "__main__":
    main()
