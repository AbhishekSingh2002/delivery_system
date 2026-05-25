import json
import math
import csv
import random
from pathlib import Path


# calculate straight line distance between two points
def euclidean_distance(point_a, point_b):
    return math.sqrt((point_b[0] - point_a[0]) ** 2 + (point_b[1] - point_a[1]) ** 2)


# read the json file and return the data
def load_data(filepath):
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    with path.open(encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {filepath}: {exc}") from exc


# the json files can be in two formats - dict style or list style
# this function handles both and converts them to one standard format
def normalize_data(raw):
    raw_wh = raw.get("warehouses", {})
    raw_ag = raw.get("agents", {})
    raw_pk = raw.get("packages", [])

    # handle list format: [{"id": "W1", "location": [x, y]}]
    if isinstance(raw_wh, list):
        warehouses = {w["id"]: w["location"] for w in raw_wh}
    else:
        # handle dict format: {"W1": [x, y]}
        warehouses = dict(raw_wh)

    if isinstance(raw_ag, list):
        agents = {a["id"]: a["location"] for a in raw_ag}
    else:
        agents = dict(raw_ag)

    # some files use "warehouse", others use "warehouse_id" - handle both
    packages = []
    for pkg in raw_pk:
        warehouse_key = pkg.get("warehouse") or pkg.get("warehouse_id")
        packages.append({
            "id": pkg["id"],
            "warehouse": warehouse_key,
            "destination": pkg["destination"],
        })

    # make sure every package points to a real warehouse
    for pkg in packages:
        if pkg["warehouse"] not in warehouses:
            raise ValueError(
                f"Package {pkg['id']} has unknown warehouse '{pkg['warehouse']}'"
            )

    return warehouses, agents, packages


# assign each package to the nearest agent (nearest to the warehouse)
def assign_packages(packages, warehouses, agents):
    # copy positions so we don't mess up the original agent locations
    current_positions = {aid: list(loc) for aid, loc in agents.items()}

    # start with empty list for each agent
    assignments = {aid: [] for aid in agents}

    for pkg in packages:
        warehouse_loc = warehouses[pkg["warehouse"]]

        # find which agent is closest to this warehouse right now
        nearest_agent = min(
            current_positions,
            key=lambda aid: euclidean_distance(current_positions[aid], warehouse_loc),
        )

        assignments[nearest_agent].append(pkg)

        # after delivery, agent is now at the destination (ready for next package)
        current_positions[nearest_agent] = list(pkg["destination"])

    return assignments


# possible random delay events to make simulation realistic
_DELAY_EVENTS = [
    ("traffic jam", 5, 20),
    ("weather delay", 10, 30),
    ("fuel stop", 5, 15),
    ("road closure", 15, 45),
    ("no delay", 0, 0),   # no delay is most common
    ("no delay", 0, 0),
    ("no delay", 0, 0),
]


def _random_delay():
    event, lo, hi = random.choice(_DELAY_EVENTS)
    return event, random.randint(lo, hi) if hi > 0 else 0


# simulate the full delivery route for every agent and calculate distances
def simulate_deliveries(assignments, agents, warehouses, use_delays=True):
    delivery_log = {}

    for agent_id, pkgs in assignments.items():
        start_pos = list(agents[agent_id])
        current_pos = list(start_pos)
        total_distance = 0.0
        pkg_logs = []

        for pkg in pkgs:
            wh_loc = warehouses[pkg["warehouse"]]
            dest = pkg["destination"]

            # leg 1: agent travels from current position to the warehouse
            pickup_dist = euclidean_distance(current_pos, wh_loc)

            # leg 2: agent travels from warehouse to customer
            delivery_dist = euclidean_distance(wh_loc, dest)

            total_distance += pickup_dist + delivery_dist

            # add a random delay if enabled
            delay_event, delay_mins = ("none", 0)
            if use_delays:
                delay_event, delay_mins = _random_delay()

            pkg_logs.append({
                "id":                pkg["id"],
                "warehouse":         pkg["warehouse"],
                "warehouse_loc":     list(wh_loc),
                "destination":       list(dest),
                "pickup_distance":   round(pickup_dist, 4),
                "delivery_distance": round(delivery_dist, 4),
                "delay_event":       delay_event,
                "delay_minutes":     delay_mins,
            })

            # agent is now at the delivery destination
            current_pos = list(dest)

        delivery_log[agent_id] = {
            "start":          start_pos,
            "packages":       pkg_logs,
            "total_distance": round(total_distance, 4),
        }

    return delivery_log


# build the final performance report for all agents
def generate_report(delivery_log, agents):
    report_agents = {}

    for agent_id in agents:
        log = delivery_log.get(agent_id, {})
        pkgs_delivered = len(log.get("packages", []))
        total_dist = log.get("total_distance", 0.0)

        # efficiency = distance per package (lower is better)
        efficiency = round(total_dist / pkgs_delivered, 4) if pkgs_delivered > 0 else 0.0

        report_agents[agent_id] = {
            "packages_delivered": pkgs_delivered,
            "total_distance":     round(total_dist, 2),
            "efficiency":         round(efficiency, 2),
        }

    # best agent = one who traveled least per package
    active_agents = {
        aid: s for aid, s in report_agents.items() if s["packages_delivered"] > 0
    }

    if active_agents:
        best_agent = min(
            active_agents,
            key=lambda aid: (active_agents[aid]["efficiency"], aid),
        )
    else:
        best_agent = None

    return {"agents": report_agents, "best_agent": best_agent}


# print each agent's route in a readable format
def visualise_routes_ascii(delivery_log, agents, warehouses):
    print("\n── ASCII Route Visualisation ──────────────────────────────")
    for agent_id, log in delivery_log.items():
        start = log["start"]
        print(f"\n  Agent {agent_id}  [start: ({start[0]}, {start[1]})]")

        if not log["packages"]:
            print("    (no packages assigned)")
            continue

        for pkg in log["packages"]:
            wloc = pkg["warehouse_loc"]
            dest = pkg["destination"]
            delay_str = (
                f"{pkg['delay_event']} +{pkg['delay_minutes']}min"
                if pkg["delay_minutes"] > 0
                else "on time"
            )
            print(
                f"    📦 {pkg['id']}  "
                f"→ {pkg['warehouse']}({wloc[0]},{wloc[1]})  "
                f"→ Customer({dest[0]},{dest[1]})  "
                f"[pickup: {pkg['pickup_distance']:.2f}  "
                f"delivery: {pkg['delivery_distance']:.2f}  "
                f"⏱ {delay_str}]"
            )

        print(f"    ─ Total distance: {log['total_distance']:.2f}")
    print()


# export agent performance to a csv file, sorted by efficiency
def export_csv(report, filename="top_agents.csv"):
    agents_data = report["agents"]
    best_agent = report["best_agent"]

    # sort: best performers first, agents with no deliveries go to bottom
    def sort_key(item):
        aid, stats = item
        return (0 if stats["packages_delivered"] > 0 else 1, stats["efficiency"], aid)

    sorted_agents = sorted(agents_data.items(), key=sort_key)

    with open(filename, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["rank", "agent_id", "packages_delivered",
                        "total_distance", "efficiency", "is_best"],
        )
        writer.writeheader()

        for rank, (agent_id, stats) in enumerate(sorted_agents, start=1):
            writer.writerow({
                "rank":               rank,
                "agent_id":           agent_id,
                "packages_delivered": stats["packages_delivered"],
                "total_distance":     stats["total_distance"],
                "efficiency":         stats["efficiency"],
                "is_best":            "YES" if agent_id == best_agent else "",
            })