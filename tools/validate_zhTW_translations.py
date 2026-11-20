#!/usr/bin/env python3
"""Validate the CP950 WARP translation map against an untouched client EXE.

The mapping file is JSON syntax, which is also valid YAML 1.2 and is accepted by
WARP's YAML loader. This tool only reads files; it never patches the EXE.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path


def hex_payload(value: str, field: str) -> bytes:
    match = re.fullmatch(r"\s*<\s*([0-9A-Fa-f ]+)\s*>\s*", value or "")
    if not match:
        raise ValueError(f"{field} must be a hex payload wrapped in angle brackets")
    tokens = match.group(1).split()
    if any(len(token) != 2 for token in tokens):
        raise ValueError(f"{field} contains a non-byte hex token")
    return bytes(int(token, 16) for token in tokens)


def placeholders(value: bytes) -> list[bytes]:
    return re.findall(rb"%(?:[0-9]+\$)?[ds]", value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path, help="Untouched client EXE")
    parser.add_argument("--mapping", type=Path,
                        default=Path("localization/Translations_zhTW.yml"))
    args = parser.parse_args()

    exe = args.exe.read_bytes()
    mapping_bytes = args.mapping.read_bytes()
    entries = json.loads(mapping_bytes.decode("utf-8"))
    if not isinstance(entries, list) or not entries:
        raise ValueError("Translation mapping must be a non-empty list")

    report = []
    errors = []
    used_offsets = set()
    for index, entry in enumerate(entries):
        desc = entry.get("desc", f"entry-{index}")
        find = hex_payload(entry.get("find"), f"{desc}.find")
        replace = hex_payload(entry.get("replace"), f"{desc}.replace")
        if not find or not replace:
            errors.append(f"{desc}: empty find/replace payload")
            continue
        if b"\0" in replace:
            errors.append(f"{desc}: replacement payload must not include NUL; WARP appends it")
        pattern = b"\0" + find + b"\0"
        offsets = []
        pos = 0
        while True:
            found = exe.find(pattern, pos)
            if found < 0:
                break
            offsets.append(found)
            pos = found + 1
        if len(offsets) != 1:
            errors.append(f"{desc}: expected one WARP search match, found {len(offsets)}")
            continue

        match_offset = offsets[0]
        text_start = match_offset + 1
        end = text_start + len(find)
        zero_padding = 0
        while end + zero_padding < len(exe) and exe[end + zero_padding] == 0:
            zero_padding += 1
        capacity = len(find) + zero_padding
        required = len(replace) + 1  # WARP appends one NUL byte
        source_placeholders = placeholders(find)
        replacement_placeholders = placeholders(replace)
        if sorted(source_placeholders) != sorted(replacement_placeholders):
            errors.append(f"{desc}: printf placeholders differ "
                          f"({source_placeholders!r} != {replacement_placeholders!r})")
        if required > capacity:
            errors.append(f"{desc}: replacement needs {required} bytes, "
                          f"available contiguous string/padding capacity is {capacity}")
        if match_offset in used_offsets:
            errors.append(f"{desc}: overlapping search offset")
        used_offsets.add(match_offset)
        report.append({
            "desc": desc,
            "match_offset_including_leading_nul": f"0x{match_offset:X}",
            "text_start_offset": f"0x{text_start:X}",
            "source_find_bytes": len(find),
            "replacement_cp950_bytes": len(replace),
            "zero_padding_after_find": zero_padding,
            "available_capacity_bytes": capacity,
            "required_bytes_including_terminator": required,
            "fits_without_overwriting_nonzero_data": required <= capacity,
            "placeholders_preserved": sorted(source_placeholders) == sorted(replacement_placeholders),
            "cp950_roundtrip": cp950_roundtrip,
        })

    result = {
        "exe": args.exe.name,
        "exe_size": len(exe),
        "exe_sha256": hashlib.sha256(exe).hexdigest(),
        "mapping": str(args.mapping),
        "mapping_sha256": hashlib.sha256(mapping_bytes).hexdigest(),
        "encoding": "Windows-950 / CP950 (Big5)",
        "entry_count": len(entries),
        "validated_entry_count": len(report),
        "errors": errors,
        "entries": report,
        "patched_exe_created": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
