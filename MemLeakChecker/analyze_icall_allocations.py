import argparse
import csv
import os
import re
from collections import defaultdict, deque

MALLOC_WITH_SIZE_RE = re.compile(r"ICall_malloc\s+size\s+(\d+)\s*,\s*add\s+([0-9A-Fa-fx]+)", re.IGNORECASE)
MALLOC_ADDR_RE = re.compile(r"ICall_malloc(?:\s+[^:]+)?\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
L2CAP_BM_ALLOC_RE = re.compile(r"L2CAP_bm_alloc\s+allocating\s+(\d+)\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
L2CAP_MALLOC_RE = re.compile(r"L2CAP_Malloc\s+size\s*:\s*(\d+)\s*,\s*addr\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
FREE_RE = re.compile(r"ICall_free(?:\s+[^:]+)?\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
FREE_MSG_RE = re.compile(r"ICall_freeMsg(?:\s+[^:]+)?\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
FREE_LEGACY_RE = re.compile(r"ICall_free\s+msg\s+([0-9A-Fa-fx]+)", re.IGNORECASE)
FREE_MSG_LEGACY_RE = re.compile(r"ICall_freeMsg\s+msg\s+([0-9A-Fa-fx]+)", re.IGNORECASE)
L2CAP_FREE_TX_SDU_RE = re.compile(r"l2capFreeTxSDU\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
L2CAP_FREE_ADDR_RE = re.compile(r"L2CAP_Free\s+addr\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
L2CAP_FREE_RX_RE = re.compile(r"L2CAP_free\s+Rx\s*:\s*([0-9A-Fa-fx]+)", re.IGNORECASE)
L2CAP_PROCESS_DATA_FREE_RE = re.compile(r"l2capProcessData\s*:\s*freeing\s+([0-9A-Fa-fx]+)", re.IGNORECASE)
L2CAP_FREE_CHANNEL_RE = re.compile(r"l2capFreeChannel\s*:\s*freeing\s+pCoC\s+([0-9A-Fa-fx]+)", re.IGNORECASE)


def normalize_addr(addr: str) -> str:
    addr = addr.strip().lower()
    if addr.startswith("0x"):
        addr = addr[2:]
    return addr


def parse_message(msg: str):
    malloc_with_size_match = MALLOC_WITH_SIZE_RE.search(msg)
    if malloc_with_size_match:
        size = int(malloc_with_size_match.group(1))
        addr = normalize_addr(malloc_with_size_match.group(2))
        return "malloc", addr, size

    l2cap_bm_alloc_match = L2CAP_BM_ALLOC_RE.search(msg)
    if l2cap_bm_alloc_match:
        size = int(l2cap_bm_alloc_match.group(1))
        addr = normalize_addr(l2cap_bm_alloc_match.group(2))
        return "malloc", addr, size

    l2cap_malloc_match = L2CAP_MALLOC_RE.search(msg)
    if l2cap_malloc_match:
        size = int(l2cap_malloc_match.group(1))
        addr = normalize_addr(l2cap_malloc_match.group(2))
        return "malloc", addr, size

    malloc_addr_match = MALLOC_ADDR_RE.search(msg)
    if malloc_addr_match:
        addr = normalize_addr(malloc_addr_match.group(1))
        return "malloc", addr, None

    l2cap_free_tx_sdu_match = L2CAP_FREE_TX_SDU_RE.search(msg)
    if l2cap_free_tx_sdu_match:
        addr = normalize_addr(l2cap_free_tx_sdu_match.group(1))
        return "free", addr, None

    l2cap_free_addr_match = L2CAP_FREE_ADDR_RE.search(msg)
    if l2cap_free_addr_match:
        addr = normalize_addr(l2cap_free_addr_match.group(1))
        return "free", addr, None

    l2cap_free_rx_match = L2CAP_FREE_RX_RE.search(msg)
    if l2cap_free_rx_match:
        addr = normalize_addr(l2cap_free_rx_match.group(1))
        return "free", addr, None

    l2cap_process_data_free_match = L2CAP_PROCESS_DATA_FREE_RE.search(msg)
    if l2cap_process_data_free_match:
        addr = normalize_addr(l2cap_process_data_free_match.group(1))
        return "free", addr, None

    l2cap_free_channel_match = L2CAP_FREE_CHANNEL_RE.search(msg)
    if l2cap_free_channel_match:
        addr = normalize_addr(l2cap_free_channel_match.group(1))
        return "free", addr, None

    freemsg_match = FREE_MSG_RE.search(msg)
    if freemsg_match:
        addr = normalize_addr(freemsg_match.group(1))
        return "freemsg", addr, None

    freemsg_legacy_match = FREE_MSG_LEGACY_RE.search(msg)
    if freemsg_legacy_match:
        addr = normalize_addr(freemsg_legacy_match.group(1))
        return "freemsg", addr, None

    free_match = FREE_RE.search(msg)
    if free_match:
        addr = normalize_addr(free_match.group(1))
        return "free", addr, None

    free_legacy_match = FREE_LEGACY_RE.search(msg)
    if free_legacy_match:
        addr = normalize_addr(free_legacy_match.group(1))
        return "free", addr, None

    return None, None, None


def parse_event_from_row(row, payload_column=None):
    if payload_column is not None:
        if payload_column >= len(row):
            return None, None, None, None
        cell = row[payload_column]
        if not cell:
            return None, None, None, None
        event_type, addr, size = parse_message(cell)
        if event_type is not None:
            return event_type, addr, size, cell
        return None, None, None, None

    for cell in row:
        if not cell:
            continue
        event_type, addr, size = parse_message(cell)
        if event_type is not None:
            return event_type, addr, size, cell
    return None, None, None, None


def parse_event_and_column_from_row(row):
    for index, cell in enumerate(row):
        if not cell:
            continue
        event_type, addr, size = parse_message(cell)
        if event_type is not None:
            return event_type, addr, size, cell, index
    return None, None, None, None, None


def analyze(
    csv_path: str,
    output_path: str,
    progress_interval_mb: int = 25,
    payload_column=None,
    learn_payload_column: bool = False,
    match_order: str = "lifo",
    suspected_free_mode: str = "apply",
):
    file_size = os.path.getsize(csv_path)
    progress_interval_bytes = max(1, progress_interval_mb * 1024 * 1024)
    next_progress_mark = progress_interval_bytes

    open_allocations = defaultdict(deque)
    unmatched_frees = []
    suspected_frees = []

    malloc_count = 0
    free_count = 0
    matched_count = 0
    ignored_rows = 0
    processed_rows = 0
    active_payload_column = payload_column
    learned_column = None

    bytes_read = 0

    with open(csv_path, "r", encoding="utf-8", newline="") as csv_file:
        for raw_line in csv_file:
            bytes_read += len(raw_line.encode("utf-8", errors="ignore"))
            row = next(csv.reader([raw_line]))
            processed_rows += 1
            if not row:
                ignored_rows += 1
            else:
                if active_payload_column is not None:
                    event_type, addr, size, message = parse_event_from_row(row, active_payload_column)
                elif learn_payload_column:
                    event_type, addr, size, message, discovered_column = parse_event_and_column_from_row(row)
                    if discovered_column is not None:
                        active_payload_column = discovered_column
                        learned_column = discovered_column
                        print(f"Learned payload column: {learned_column} (zero-based)")
                else:
                    event_type, addr, size, message = parse_event_from_row(row)

                if event_type == "malloc":
                    malloc_count += 1
                    if open_allocations[addr] and suspected_free_mode != "off":
                        if match_order == "fifo":
                            inferred_freed = open_allocations[addr][0]
                        else:
                            inferred_freed = open_allocations[addr][-1]

                        suspected_frees.append(
                            (
                                inferred_freed[0],
                                addr,
                                processed_rows,
                                inferred_freed[2],
                                message,
                            )
                        )

                        if suspected_free_mode == "apply":
                            if match_order == "fifo":
                                open_allocations[addr].popleft()
                            else:
                                open_allocations[addr].pop()

                    open_allocations[addr].append((processed_rows, size, message))
                elif event_type in ("free", "freemsg"):
                    free_count += 1
                    if open_allocations[addr]:
                        if match_order == "fifo":
                            open_allocations[addr].popleft()
                        else:
                            open_allocations[addr].pop()
                        matched_count += 1
                        if not open_allocations[addr]:
                            del open_allocations[addr]
                    else:
                        unmatched_frees.append((processed_rows, event_type, addr, message))
                else:
                    ignored_rows += 1

            if bytes_read >= next_progress_mark or bytes_read == file_size:
                percent = (bytes_read / file_size * 100.0) if file_size else 100.0
                print(
                    f"Progress: {percent:6.2f}% | rows={processed_rows:,} | "
                    f"malloc={malloc_count:,} free={free_count:,} matched={matched_count:,}"
                )
                while next_progress_mark <= bytes_read:
                    next_progress_mark += progress_interval_bytes

    unmatched_mallocs = []
    for addr, allocations in open_allocations.items():
        for line_num, size, message in allocations:
            unmatched_mallocs.append((line_num, addr, size, message))

    unmatched_mallocs.sort(key=lambda x: x[0])
    unmatched_frees.sort(key=lambda x: x[0])
    unmatched_malloc_total_bytes = sum(size for _, _, size, _ in unmatched_mallocs if size is not None)
    unmatched_malloc_unknown_size_count = sum(1 for _, _, size, _ in unmatched_mallocs if size is None)

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("ICall allocation/deallocation mismatch report\n")
        out.write(f"Input file: {csv_path}\n")
        out.write(f"Match order: {match_order}\n")
        out.write(f"Suspected free mode: {suspected_free_mode}\n")
        if active_payload_column is not None:
            out.write(f"Payload column used: {active_payload_column} (zero-based)\n")
        else:
            out.write("Payload column used: auto-scan per row\n")
        out.write(f"Processed rows: {processed_rows:,}\n")
        out.write(f"Matched pairs: {matched_count:,}\n")
        out.write(f"Unmatched mallocs: {len(unmatched_mallocs):,}\n")
        out.write(f"Unmatched malloc total bytes: {unmatched_malloc_total_bytes:,}\n")
        out.write(f"Unmatched mallocs with unknown size: {unmatched_malloc_unknown_size_count:,}\n")
        out.write(f"Unmatched frees: {len(unmatched_frees):,}\n")
        out.write(f"Suspected frees inferred by re-malloc: {len(suspected_frees):,}\n")
        out.write(f"Ignored rows: {ignored_rows:,}\n")
        out.write("\n")

        out.write("=== Unmatched malloc allocations (not freed) ===\n")
        if unmatched_mallocs:
            for line_num, addr, size, message in unmatched_mallocs:
                size_text = str(size) if size is not None else "unknown"
                out.write(
                    f"line={line_num}, addr=0x{addr}, size={size_text}, event={message}\n"
                )
        else:
            out.write("None\n")

        out.write("\n=== Unmatched deallocations (free/freeMsg without prior malloc) ===\n")
        if unmatched_frees:
            for line_num, event_type, addr, message in unmatched_frees:
                out.write(
                    f"line={line_num}, type={event_type}, addr=0x{addr}, event={message}\n"
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
    print(f"Rows processed: {processed_rows:,}")
    print(f"Matched pairs: {matched_count:,}")
    print(f"Unmatched mallocs: {len(unmatched_mallocs):,}")
    print(f"Unmatched malloc total bytes: {unmatched_malloc_total_bytes:,}")
    print(f"Unmatched mallocs with unknown size: {unmatched_malloc_unknown_size_count:,}")
    print(f"Unmatched frees: {len(unmatched_frees):,}")
    print(f"Suspected frees inferred by re-malloc: {len(suspected_frees):,}")
    print(f"Ignored rows: {ignored_rows:,}")
    if learned_column is not None:
        print(f"Learned payload column: {learned_column} (zero-based)")
    elif active_payload_column is not None:
        print(f"Payload column used: {active_payload_column} (zero-based)")
    else:
        print("Payload column mode: auto-scan per row")
    print(f"Report written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyze TIlogger CSV logs to match ICall_malloc allocations with "
            "ICall_free/ICall_freeMsg deallocations."
        )
    )
    parser.add_argument("csv_file", help="Path to input CSV file")
    parser.add_argument(
        "-o",
        "--output",
        default="icall_mismatch_report.txt",
        help="Path to output text report (default: icall_mismatch_report.txt)",
    )
    parser.add_argument(
        "--progress-mb",
        type=int,
        default=25,
        help="Print progress every N MB read (default: 25)",
    )
    parser.add_argument(
        "--payload-column",
        type=int,
        default=None,
        help=(
            "Optional zero-based CSV column index containing the ICall payload string. "
            "If omitted, all columns are scanned."
        ),
    )
    parser.add_argument(
        "--learn-payload-column",
        action="store_true",
        help=(
            "Learn payload column from the first row containing an ICall event, "
            "then use that column for the rest of the file."
        ),
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

    if not os.path.exists(args.csv_file):
        raise FileNotFoundError(f"Input CSV not found: {args.csv_file}")

    if args.payload_column is not None and args.payload_column < 0:
        raise ValueError("--payload-column must be a non-negative integer")

    if args.payload_column is not None and args.learn_payload_column:
        raise ValueError("Use either --payload-column or --learn-payload-column, not both")
    if args.progress_mb <= 0:
        raise ValueError("--progress-mb must be a positive integer")

    analyze(
        args.csv_file,
        args.output,
        args.progress_mb,
        args.payload_column,
        args.learn_payload_column,
        args.match_order,
        args.suspected_free_mode,
    )


if __name__ == "__main__":
    main()
