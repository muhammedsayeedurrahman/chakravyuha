"""Download BNS/IPC data from public sources (placeholder helpers)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import DATA_DIR


def verify_data_files():
    """Verify that all required data files exist and are valid JSON."""
    required_files = [
        "bns_sections.json",
        "ipc_sections.json",
        "ipc_to_bns_mapping.json",
        "guided_flow_tree.json",
        "defence_strategies.json",
        "test_queries.json",
    ]

    all_ok = True
    for filename in required_files:
        path = DATA_DIR / filename
        if not path.exists():
            print(f"  MISSING: {filename}")
            all_ok = False
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            size = path.stat().st_size
            print(f"  OK: {filename} ({size:,} bytes)")
        except json.JSONDecodeError as e:
            print(f"  INVALID JSON: {filename} — {e}")
            all_ok = False

    return all_ok


def print_data_stats():
    """Print statistics about the loaded data."""
    with open(DATA_DIR / "bns_sections.json", "r", encoding="utf-8") as f:
        bns = json.load(f)
    with open(DATA_DIR / "ipc_sections.json", "r", encoding="utf-8") as f:
        ipc = json.load(f)
    with open(DATA_DIR / "ipc_to_bns_mapping.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    with open(DATA_DIR / "guided_flow_tree.json", "r", encoding="utf-8") as f:
        tree = json.load(f)
    with open(DATA_DIR / "defence_strategies.json", "r", encoding="utf-8") as f:
        defences = json.load(f)
    with open(DATA_DIR / "test_queries.json", "r", encoding="utf-8") as f:
        tests = json.load(f)

    print(f"\n  BNS sections: {len(bns['sections'])}")
    print(f"  IPC sections: {len(ipc['sections'])}")
    print(f"  IPC->BNS mappings: {len(mapping['mappings'])}")
    print(f"  New BNS sections (no IPC equiv): {len(mapping.get('new_in_bns', []))}")
    print(f"  Guided flow nodes: {len(tree)}")
    terminal_nodes = sum(1 for v in tree.values() if isinstance(v, dict) and v.get("terminal"))
    print(f"  Guided flow terminal nodes: {terminal_nodes}")
    print(f"  Defence strategies: {len(defences['strategies'])}")
    print(f"  Test queries: {len(tests['queries'])}")


def main():
    print("Chakravyuha Data Verification")
    print("=" * 40)
    print("\nChecking data files...")
    ok = verify_data_files()

    if ok:
        print("\nAll data files OK!")
        print_data_stats()
    else:
        print("\nSome files are missing or invalid.")
        print("The data files should already be in the data/ directory.")
        print("If they're missing, check the git repository.")


if __name__ == "__main__":
    main()
