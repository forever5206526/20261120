#!/usr/bin/env python3
"""Read-only signature checks for selected WARP patches on a Ragnarok client EXE.

This utility never executes or modifies the supplied executable.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_pattern(data: bytes, pattern: str, limit: int = 20) -> list[int]:
    tokens = pattern.split()
    values, mask = [], []
    for token in tokens:
        wildcard = "?" in token
        values.append(0 if wildcard else int(token, 16))
        mask.append(not wildcard)
    if not values or not any(mask):
        return []
    first = next(i for i, fixed in enumerate(mask) if fixed)
    needle, hits, pos = bytes([values[first]]), [], 0
    while len(hits) < limit:
        found = data.find(needle, pos)
        if found < 0:
            break
        start = found - first
        if start >= 0 and start + len(values) <= len(data):
            if all(not mask[i] or data[start + i] == values[i] for i in range(len(values))):
                hits.append(start)
        pos = found + 1
    return hits


def parse_pe(data: bytes) -> dict:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("Missing MZ header")
    peoff = struct.unpack_from("<I", data, 0x3C)[0]
    if peoff + 24 > len(data) or data[peoff:peoff + 4] != b"PE\0\0":
        raise ValueError("Missing PE signature")
    machine, count, timestamp, _, _, opt_size, characteristics = struct.unpack_from(
        "<HHIIIHH", data, peoff + 4
    )
    opt = peoff + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x10B:
        image_base = struct.unpack_from("<I", data, opt + 28)[0]
    elif magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, opt + 24)[0]
    else:
        raise ValueError(f"Unsupported optional-header magic: {magic:#x}")
    sections = []
    for i in range(count):
        off = opt + opt_size + i * 40
        name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
        vsize, rva, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        sections.append({"name": name, "rva": rva, "virtual_size": vsize,
                         "raw_size": raw_size, "raw_ptr": raw_ptr})
    return {"machine": machine, "timestamp": timestamp, "magic": magic,
            "image_base": image_base, "characteristics": characteristics,
            "sections": sections}


def offset_to_va(pe: dict, offset: int) -> int | None:
    for sec in pe["sections"]:
        if sec["raw_ptr"] <= offset < sec["raw_ptr"] + sec["raw_size"]:
            return pe["image_base"] + sec["rva"] + offset - sec["raw_ptr"]
    return None


def rva_to_offset(pe: dict, rva: int) -> int | None:
    for sec in pe["sections"]:
        span = max(sec["virtual_size"], sec["raw_size"])
        if sec["rva"] <= rva < sec["rva"] + span:
            offset = sec["raw_ptr"] + rva - sec["rva"]
            return offset if offset < sec["raw_ptr"] + sec["raw_size"] else None
    return None


def parse_imports(data: bytes, pe: dict) -> dict[str, list[str]]:
    # Import directory is data-directory entry 1.
    peoff = struct.unpack_from("<I", data, 0x3C)[0]
    opt = peoff + 24
    directory_offset = opt + (96 if pe["magic"] == 0x10B else 112)
    import_rva, _ = struct.unpack_from("<II", data, directory_offset + 8)
    descriptor = rva_to_offset(pe, import_rva) if import_rva else None
    result: dict[str, list[str]] = {}
    if descriptor is None:
        return result

    thunk_size = 4 if pe["magic"] == 0x10B else 8
    ordinal_mask = 0x80000000 if thunk_size == 4 else 0x8000000000000000
    while descriptor + 20 <= len(data):
        oft, _, _, name_rva, first_thunk = struct.unpack_from("<IIIII", data, descriptor)
        if not any((oft, name_rva, first_thunk)):
            break
        name_off = rva_to_offset(pe, name_rva)
        if name_off is None:
            descriptor += 20
            continue
        name_end = data.find(b"\\0", name_off)
        dll_name = data[name_off:name_end].decode("ascii", "replace").lower()
        names = result.setdefault(dll_name, [])
        thunk_rva = oft or first_thunk
        thunk_off = rva_to_offset(pe, thunk_rva)
        if thunk_off is not None:
            index = 0
            while thunk_off + (index + 1) * thunk_size <= len(data):
                value = int.from_bytes(data[thunk_off + index * thunk_size:
                                            thunk_off + (index + 1) * thunk_size], "little")
                if value == 0:
                    break
                if not (value & ordinal_mask):
                    import_name_off = rva_to_offset(pe, value)
                    if import_name_off is not None and import_name_off + 2 < len(data):
                        end = data.find(b"\\0", import_name_off + 2)
                        names.append(data[import_name_off + 2:end].decode("ascii", "replace"))
                index += 1
        descriptor += 20
    return result


def hits(data: bytes, pattern: str) -> dict:
    found = find_pattern(data, pattern)
    return {"count": len(found), "offsets": [f"0x{x:X}" for x in found]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path, help="Input EXE; opened read-only")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    data = args.exe.read_bytes()
    pe = parse_pe(data)
    stamp = pe["timestamp"]

    checks = {
        "UseOldLogin_2026_gate": hits(data,
            "8B 0D ?? ?? ?? ?? 85 C9 0F 84 ?? ?? ?? ?? 83 F9 12 0F 84 ?? ?? ?? ?? "
            "83 F9 0C 0F 84 ?? ?? ?? ?? 0F 10 87 78 01 00 00 B8 64 00 00 00"),
        "UseOldLogin_2026_modern_packet_builder": hits(data,
            "85 C0 0F 84 ?? ?? ?? ?? 6A 44 8D 45 A0 6A 00 50 E8 ?? ?? ?? ?? B8 CF 0A 00 00"),
        "NoLoginOTP": hits(data, "6A 26 68 35 27 00 00 FF 50 18"),
        "GoldPC_PUSH_300": hits(data, "68 2C 01 00 00 68 3B 0A 00 00 E8 ?? ?? ?? ??"),
        "GoldPC_CMP_EDI_primary": hits(data, "81 BF 98 00 00 00 2C 01 00 00"),
        "GoldPC_CMP_EDI_fallback": hits(data, "81 BF ?? ?? ?? ?? 2C 01 00 00 0F 8C ?? ?? ?? ??"),
        "GoldPC_CMP_ESI_primary": hits(data, "81 BE 98 00 00 00 2C 01 00 00"),
        "GoldPC_CMP_ESI_fallback": hits(data, "81 BE ?? ?? ?? ?? 2C 01 00 00 7D 73"),
    }

    # TranslateClient's hex search wraps each target with leading/trailing NUL.
    translation_patterns = {
        "Deletion_Time_Part_2": "25 64 B3 E2 20 25 64 BF F9 20 25 64 C0 CF 20 25 64 BD C3 20 25 64 BA D0 20 25 64 C3 CA 20",
        "Message_Box": "B8 DE BD C3 C1 F6 00",
        "Total_in_Cash_Shop": "54 6F 74 61 6C 20 3A 20 25 64 20 C4 B3 BD C3",
        "Pet_Evolution_Item_Amount": "25 64 B0 B3 00",
        "Tip_Box_Part_2": "B4 DD B1 E2",
        "Equipment_Dismount_Cart": "C4 AB C6 AE 20 C7 D8 C1 A6",
        "No_Color": "BF B0 BB F6 C1 A6 B0 C5",
        "Rune_Tablet_Rune_List": "25 73 C0 C7 20 B7 E9 20 C1 B6 B0 A2",
    }
    checks["TranslateClient_candidate_strings"] = {
        name: hits(data, "00 " + pattern + " 00")
        for name, pattern in translation_patterns.items()
    }

    anchor = b"_emblem.bmp\0"
    anchor_off = data.find(anchor)
    cps = {"anchor_count": data.count(anchor), "anchor_file_offset": None,
           "anchor_va": None, "push_pointer_offsets": [],
           "preceding_e8_opcode_candidates": []}
    if anchor_off >= 0:
        anchor_va = offset_to_va(pe, anchor_off)
        cps["anchor_file_offset"] = f"0x{anchor_off:X}"
        cps["anchor_va"] = f"0x{anchor_va:X}" if anchor_va is not None else None
        if anchor_va is not None:
            push = b"\x68" + struct.pack("<I", anchor_va)
            pos = 0
            while True:
                hit = data.find(push, pos)
                if hit < 0:
                    break
                cps["push_pointer_offsets"].append(f"0x{hit:X}")
                for call_off in range(max(0, hit - 0x20), hit):
                    if data[call_off] == 0xE8 and call_off + 5 <= hit:
                        cps["preceding_e8_opcode_candidates"].append(f"0x{call_off:X}")
                pos = hit + 1
    checks["RestoreCpsDll_anchor"] = cps

    import_names = ("GetModuleHandleA", "GetProcAddress", "OutputDebugStringA",
                    "CreateWindowExA", "MessageBoxA", "wsprintfA", "_setmbcp")
    report = {
        "input_filename": args.exe.name,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "pe": {
            "machine": f"0x{pe['machine']:04X}",
            "architecture": "Intel i386 / 32-bit" if pe["machine"] == 0x14C else "Other",
            "format": "PE32" if pe["magic"] == 0x10B else "PE32+",
            "timestamp_epoch": stamp,
            "timestamp_utc": datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
            "image_base": f"0x{pe['image_base']:X}",
            "sections": pe["sections"],
        },
        "import_name_strings_present_in_file": {
            name: name.encode("ascii") in data for name in import_names
        },
        "parsed_imports": {
            dll: sorted(set(names)) for dll, names in parse_imports(data, pe).items()
            if dll == "ucrtbase.dll"
        },
        "static_signature_checks": checks,
        "limitations": [
            "Raw byte signature checks only; WARP itself and its validate functions were not run.",
            "A signature match does not prove patch application, runtime stability, or successful login.",
            "The PE timestamp is not necessarily the WARP-parsed Exe.BuildDate.",
            "The input executable is never modified.",
        ],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
