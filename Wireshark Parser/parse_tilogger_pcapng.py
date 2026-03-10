#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import struct
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List


SECTION_HEADER_BLOCK = 0x0A0D0D0A
INTERFACE_DESCRIPTION_BLOCK = 0x00000001
ENHANCED_PACKET_BLOCK = 0x00000006


@dataclass
class TILoggerRecord:
    packet_index: int
    interface_id: int
    alias: str
    device_time: str
    opcode: str
    module: str
    log_level: str
    file: str
    line: str
    string: str
    raw_payload: str


def parse_tilogger_records(path: Path, dlt_id: int, show_progress: bool = True) -> List[TILoggerRecord]:
    records: List[TILoggerRecord] = []
    endian = "<"
    interfaces: Dict[int, int] = {}
    packet_index = 0

    file_size = path.stat().st_size
    bytes_processed = 0
    next_report_at = 0
    min_report_step = max(16 * 1024 * 1024, file_size // 200 if file_size else 16 * 1024 * 1024)
    last_report_time = 0.0

    def report_progress(force: bool = False) -> None:
        nonlocal next_report_at, last_report_time
        if not show_progress:
            return
        now = time.monotonic()
        if not force:
            if bytes_processed < next_report_at:
                return
            if now - last_report_time < 0.3:
                return

        percent = (bytes_processed / file_size * 100.0) if file_size else 100.0
        print(
            f"\rProgress: {bytes_processed:,}/{file_size:,} bytes ({percent:6.2f}%) | "
            f"Packets: {packet_index:,} | Matched records: {len(records):,}",
            end="",
            file=sys.stderr,
            flush=True,
        )
        next_report_at = bytes_processed + min_report_step
        last_report_time = now

    with path.open("rb") as f:
        while True:
            header = f.read(8)
            if not header:
                break
            if len(header) < 8:
                raise ValueError("Truncated pcapng block header")

            raw_block_type = header[:4]

            if raw_block_type == b"\x0A\x0D\x0D\x0A":
                bom = f.read(4)
                if len(bom) < 4:
                    raise ValueError("Truncated Section Header Block")

                if bom == b"\x4D\x3C\x2B\x1A":
                    endian = "<"
                elif bom == b"\x1A\x2B\x3C\x4D":
                    endian = ">"
                else:
                    raise ValueError(f"Invalid byte-order magic: {bom.hex()}")

                total_len = struct.unpack(endian + "I", header[4:8])[0]
                if total_len < 12:
                    raise ValueError(f"Invalid Section Header Block length: {total_len}")

                remaining = f.read(total_len - 12)
                if len(remaining) < total_len - 12:
                    raise ValueError("Truncated Section Header Block payload")

                interfaces = {}
                bytes_processed += total_len
                report_progress()
                continue

            block_type = struct.unpack(endian + "I", raw_block_type)[0]
            total_len = struct.unpack(endian + "I", header[4:8])[0]
            if total_len < 12:
                raise ValueError(f"Invalid block length: {total_len}")

            remaining = f.read(total_len - 8)
            if len(remaining) < total_len - 8:
                raise ValueError("Truncated pcapng block")

            body = remaining[: total_len - 12]

            if block_type == INTERFACE_DESCRIPTION_BLOCK:
                if len(body) >= 8:
                    linktype = struct.unpack_from(endian + "H", body, 0)[0]
                    interface_id = len(interfaces)
                    interfaces[interface_id] = linktype

            elif block_type == ENHANCED_PACKET_BLOCK:
                if len(body) >= 20:
                    interface_id, _ts_hi, _ts_lo, caplen, _origlen = struct.unpack_from(endian + "IIIII", body, 0)
                    payload_start = 20
                    payload_end = payload_start + caplen
                    if payload_end <= len(body):
                        packet_data = body[payload_start:payload_end]
                        if interfaces.get(interface_id) == dlt_id:
                            text = packet_data.decode("utf-8", errors="replace").strip("\x00\r\n ")
                            parts = text.split("||", 7)
                            if len(parts) == 8:
                                records.append(
                                    TILoggerRecord(
                                        packet_index=packet_index,
                                        interface_id=interface_id,
                                        alias=parts[0],
                                        device_time=parts[1],
                                        opcode=parts[2],
                                        module=parts[3],
                                        log_level=parts[4],
                                        file=parts[5],
                                        line=parts[6],
                                        string=parts[7],
                                        raw_payload=text,
                                    )
                                )

                        packet_index += 1

            bytes_processed += total_len
            report_progress()

    if show_progress:
        report_progress(force=True)
        print(file=sys.stderr)

    return records


def write_csv(path: Path, records: List[TILoggerRecord]) -> None:
    fieldnames = [
        "packet_index",
        "interface_id",
        "alias",
        "device_time",
        "opcode",
        "module",
        "log_level",
        "file",
        "line",
        "string",
        "raw_payload",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(asdict(rec))


def write_csv_selected(path: Path, records: List[TILoggerRecord]) -> None:
    fieldnames = ["packet_index", "device_time", "string"]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(
                {
                    "packet_index": rec.packet_index,
                    "device_time": rec.device_time,
                    "string": rec.string,
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse pcapng packets with a specific DLT and decode TILogger payloads."
    )
    parser.add_argument("pcapng", type=Path, help="Path to input .pcapng file")
    parser.add_argument("--dlt", type=int, default=147, help="DLT id to filter (default: 147)")
    parser.add_argument("--json", action="store_true", help="Print records as JSON")
    parser.add_argument("--csv", type=Path, help="Write records to CSV file")
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable live bytes-processed progress output",
    )
    parser.add_argument(
        "--selected-only",
        action="store_true",
        help="Output only packet_index, device_time, and string",
    )
    parser.add_argument(
        "--print-records",
        action="store_true",
        help="Print parsed records to console (disabled by default)",
    )

    args = parser.parse_args()

    if not args.pcapng.exists():
        raise FileNotFoundError(f"Input file not found: {args.pcapng}")

    records = parse_tilogger_records(args.pcapng, dlt_id=args.dlt, show_progress=not args.no_progress)

    if args.csv:
        if args.selected_only:
            write_csv_selected(args.csv, records)
        else:
            write_csv(args.csv, records)

    if args.json:
        if args.selected_only:
            selected = [
                {
                    "packet_index": r.packet_index,
                    "device_time": r.device_time,
                    "string": r.string,
                }
                for r in records
            ]
            print(json.dumps(selected, indent=2))
        else:
            print(json.dumps([asdict(r) for r in records], indent=2))
    else:
        print(f"Parsed {len(records)} TILogger records from {args.pcapng}")
        if args.print_records:
            for rec in records:
                if args.selected_only:
                    print(f"[{rec.packet_index}] {rec.device_time} | {rec.string}")
                else:
                    print(
                        f"[{rec.packet_index}] {rec.alias} | {rec.device_time} | {rec.opcode} | "
                        f"{rec.module} | {rec.log_level} | {rec.file}:{rec.line} | {rec.string}"
                    )


if __name__ == "__main__":
    main()
