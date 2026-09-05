#!/usr/bin/env python3
"""Read-only emotion catalogue lookup. No fixed emotion-to-intensity presets."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_library(path=None):
    entries = json.loads(Path(path or ROOT / "assets/emotion-library.json").read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise ValueError("emotion library must be a nonempty list")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or type(entry.get("id")) is not int:
            raise ValueError("each entry needs an integer id")
        if entry["id"] in result:
            raise ValueError("duplicate entry id")
        if any(not isinstance(entry.get(key), str) or not entry[key].strip()
               for key in ("name", "family", "intensity", "direction", "prompt")):
            raise ValueError("entry text fields must be nonempty strings")
        result[entry["id"]] = entry
    return result


def select(entries, index, ids=None, query=None):
    if ids is not None:
        missing = [i for i in ids if i not in entries]
        if missing:
            raise ValueError(f"unknown entry ids: {missing}")
        return [entries[i] for i in ids]
    if query:
        needle = query.casefold()
        return [e for i, e in entries.items()
                if needle in json.dumps([e, index.get(i, {})], ensure_ascii=False).casefold()]
    return list(entries.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--id", nargs="+", type=int)
    group.add_argument("--query")
    group.add_argument("--list", action="store_true")
    parser.add_argument("--raw", action="store_true", help="one complete body only")
    args = parser.parse_args()
    try:
        entries = load_library()
        index = {e["id"]: e for e in json.loads((ROOT / "references/emotion-index.json").read_text(encoding="utf-8"))}
        selected = select(entries, index, args.id, args.query)
        if args.raw:
            if len(selected) != 1:
                parser.error("--raw requires exactly one matching entry")
            print(selected[0]["prompt"])
        elif args.list or (args.id is None and args.query is None):
            print(json.dumps([{k: e[k] for k in ("id", "name", "family", "intensity")}
                              | {"terms": index.get(e["id"], {}).get("terms", [])}
                              for e in selected], ensure_ascii=False, indent=2))
        else:
            print(json.dumps([e | {"reading_notes": index.get(e["id"], {})} for e in selected], ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
