# FastBox Delivery Simulator
# simulates one day of delivery operations for a fictional company
# reads warehouse/agent/package data from json and generates a performance report

import sys
import json
import random
import argparse
from pathlib import Path

from utils import (
    load_data,
    normalize_data,
    assign_packages,
    simulate_deliveries,
    generate_report,
    visualise_routes_ascii,
    export_csv,
)


def parse_args():
    parser = argparse.ArgumentParser(description="FastBox Delivery Simulator")

    parser.add_argument("--input",  "-i", default="data.json",   help="Input JSON file")
    parser.add_argument("--output", "-o", default="report.json", help="Output report file")

    # bonus: add a new agent mid-day
    parser.add_argument("--add-agent", nargs=3, metavar=("ID", "X", "Y"),
                        help="Add a new agent mid-day e.g. --add-agent A4 10 20")

    parser.add_argument("--no-delays", action="store_true", help="Disable random delays")
    parser.add_argument("--ascii",     action="store_true", help="Show ASCII route map")
    parser.add_argument("--csv",       action="store_true", help="Export results to CSV")
    parser.add_argument("--seed",      type=int, default=None, help="Random seed for delays")

    return parser.parse_args()


def main():
    args = parse_args()

    # set seed so delays are reproducible if needed
    if args.seed is not None:
        random.seed(args.seed)

    # step 1: read and parse the json file
    raw = load_data(args.input)
    warehouses, agents, packages = normalize_data(raw)

    print(f"\n📦  FastBox Delivery Simulator")
    print(f"    Input  : {args.input}")
    print(f"    Warehouses : {len(warehouses)}")
    print(f"    Agents     : {len(agents)}")
    print(f"    Packages   : {len(packages)}\n")

    # bonus: inject a new agent into the system mid-day
    if args.add_agent:
        agent_id, ax, ay = args.add_agent[0], float(args.add_agent[1]), float(args.add_agent[2])
        if agent_id in agents:
            print(f"⚠️  Agent {agent_id} already exists — skipping.")
        else:
            agents[agent_id] = [ax, ay]
            print(f"🚀  New agent {agent_id} joined mid-day at ({ax}, {ay})")

    # step 2: assign each package to the nearest agent
    assignments = assign_packages(packages, warehouses, agents)

    # step 3: simulate the deliveries and calculate distances
    use_delays = not args.no_delays
    delivery_log = simulate_deliveries(assignments, agents, warehouses, use_delays)

    # bonus: show ascii route visualisation
    if args.ascii:
        visualise_routes_ascii(delivery_log, agents, warehouses)

    # step 4: generate the report
    report = generate_report(delivery_log, agents)

    # step 5: save report to json file
    out_path = Path(args.output)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\n✅  Report saved → {out_path}")

    # print summary table to the console
    best = report["best_agent"]
    print(f"\n🏆  Best agent: {best}")
    print(f"{'Agent':<8} {'Packages':>10} {'Distance':>14} {'Efficiency':>12}")
    print("─" * 48)
    for agent_id, stats in report["agents"].items():
        marker = " ◀ best" if agent_id == best else ""
        print(
            f"{agent_id:<8} {stats['packages_delivered']:>10} "
            f"{stats['total_distance']:>14.2f} "
            f"{stats['efficiency']:>12.2f}{marker}"
        )

    # bonus: export to csv
    if args.csv:
        export_csv(report, filename="top_agents.csv")
        print("\n📊  CSV exported → top_agents.csv")


if __name__ == "__main__":
    main()