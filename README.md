# FastBox Delivery Simulator

A Python-based logistics simulator for a fictional delivery company called **FastBox**.
It simulates one full day of delivery operations — assigning packages to agents, calculating travel distances, and generating a performance report.

---

## Project Structure

```
delivery_system/
├── main.py              # entry point, run this file
├── utils.py             # all core logic (distance, assignment, simulation, report)
├── test_delivery.py     # 141 automated tests
├── data.json            # sample input file
├── base_case.json       # base case from assignment
├── test_case_1.json
├── test_case_2.json
├── ...
└── test_case_10.json
```

---

## How It Works

1. Reads warehouse, agent, and package data from a JSON file
2. Assigns each package to the nearest agent (using Euclidean distance)
3. Simulates the delivery route: agent → warehouse → customer
4. Calculates total distance and efficiency for each agent
5. Saves a performance report to `report.json`

---

## How to Run

**Basic run (uses data.json by default):**
```bash
python main.py
```

**Use a specific input file:**
```bash
python main.py --input test_case_1.json
```

**Show ASCII route map:**
```bash
python main.py --input test_case_1.json --ascii
```

**Disable random delays:**
```bash
python main.py --input test_case_1.json --no-delays
```

**Add a new agent mid-day:**
```bash
python main.py --input test_case_1.json --add-agent A5 20 30
```

**Export results to CSV:**
```bash
python main.py --input test_case_1.json --csv
```

**Combine multiple flags:**
```bash
python main.py --input test_case_1.json --ascii --csv --no-delays
```

---

## Output

### report.json
```json
{
  "agents": {
    "A1": {"packages_delivered": 4, "total_distance": 75.83, "efficiency": 18.96},
    "A2": {"packages_delivered": 1, "total_distance": 34.16, "efficiency": 34.16},
    "A3": {"packages_delivered": 7, "total_distance": 184.93, "efficiency": 26.42},
    "A4": {"packages_delivered": 0, "total_distance": 0.0,   "efficiency": 0.0}
  },
  "best_agent": "A1"
}
```

### Console Summary
```
🏆  Best agent: A1
Agent      Packages       Distance   Efficiency
────────────────────────────────────────────────
A1                4          75.83        18.96 ◀ best
A2                1          34.16        34.16
A3                7         184.93        26.42
A4                0           0.00         0.00
```

---

## Efficiency Formula

```
Efficiency = Total Distance / Packages Delivered
```

Lower efficiency score = better performance (less travel per package).

---

## Input JSON Format

The program supports two formats:

**Format 1 (used in test cases):**
```json
{
  "warehouses": {"W1": [0, 0], "W2": [50, 75]},
  "agents":     {"A1": [5, 5], "A2": [60, 60]},
  "packages": [
    {"id": "P1", "warehouse": "W1", "destination": [30, 40]}
  ]
}
```

**Format 2 (used in base case):**
```json
{
  "warehouses": [{"id": "W1", "location": [0, 0]}],
  "agents":     [{"id": "A1", "location": [5, 5]}],
  "packages": [
    {"id": "P1", "warehouse_id": "W1", "destination": [30, 40]}
  ]
}
```

Both formats are handled automatically.

---

## Bonus Features

| Feature | How to use |
|---|---|
| Random delivery delays | Enabled by default, use `--no-delays` to turn off |
| ASCII route visualisation | Add `--ascii` flag |
| New agent joining mid-day | Add `--add-agent ID X Y` flag |
| CSV export | Add `--csv` flag, saves to `top_agents.csv` |

---

## Running Tests

```bash
python test_delivery.py -v
```

**141 tests** covering:
- Euclidean distance calculation
- JSON parsing (both formats)
- Package assignment logic
- Delivery simulation
- Report generation
- All 10 provided test cases + base case
- CSV export

---

## Requirements

No external libraries needed. Uses Python standard library only:

- `json` — reading/writing JSON
- `math` — distance calculation
- `csv` — CSV export
- `random` — delivery delays
- `argparse` — command line arguments
- `pathlib` — file handling