"""Estimate voltage at external servo connectors; never a hardware release gate.

Constant-current scenarios supplied by the caller, not a servo motor model.
Resistances include supply AND return paths. Requires Python 3.10+, stdlib only.
"""
import argparse
import json
import math


def nonnegative(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Inputs must be finite and nonnegative")
    return result


def estimate(source_min_v, shared_ohm, branches):
    """Branches are (current_A, external_loop_ohm) pairs, including reserves."""
    source = nonnegative(source_min_v)
    shared = nonnegative(shared_ohm)
    loads = [(nonnegative(i), nonnegative(r)) for i, r in branches]
    if not loads:
        raise ValueError("At least one branch is required")
    total = sum(i for i, _ in loads)
    drop = total * shared
    return {
        "status": "ESTIMATE_ONLY",
        "source_min_v": source,
        "total_current_a": total,
        "shared_drop_v": drop,
        "shared_loss_w": total * total * shared,
        "connector_voltage_v": [source - drop - i * r for i, r in loads],
        "branch_loss_w": [i * i * r for i, r in loads],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-min-v", required=True, type=float)
    parser.add_argument("--shared-ohm", required=True, type=float)
    parser.add_argument("--branch", required=True, action="append", metavar="AMP:OHM",
                        help="Repeat for every load, including reserves; external wiring only")
    args = parser.parse_args()
    try:
        branches = []
        for item in args.branch:
            current, resistance = item.split(":")
            branches.append((float(current), float(resistance)))
        result = estimate(args.source_min_v, args.shared_ohm, branches)
    except (ValueError, OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
