# Q4 Financial Calculations, Cash Flow Fix & Gross Profit

Calculate Q4 values, fix cumulative cash flow data, and calculate Gross Profit for financial statements.

## Quick Start

```bash
# Install dependencies (uv will handle this automatically)
# Configure environment
cp .env.example .env
# Edit .env with your MongoDB connection details
```

## CLI Commands

### Q4 Calculation

Calculate Q4 using: `Q4 = Annual - (Q1 + Q2 + Q3)`

```bash
# All companies
uv run app.py --calculate-q4 --all-companies

# Single company
uv run app.py --calculate-q4 --cik 0000789019

# Recalculate (delete existing Q4 first)
uv run app.py --calculate-q4 --all-companies --recalculate-q4
uv run app.py --calculate-q4 --cik 0000789019 --recalculate-q4
```

### Cash Flow Fix

Convert cumulative Q2/Q3 values to quarterly: `Q2 = Q2 - Q1`, `Q3 = Q3 - Q2`

```bash
# All companies
uv run app.py --fix-cashflow --all-companies

# Single company
uv run app.py --fix-cashflow --cik 0001326801

# With verbose output
uv run app.py --fix-cashflow --all-companies --verbose
```

### Gross Profit Calculation

Calculate and insert Gross Profit: `Gross Profit = Total Revenues - Cost of Revenues`

This command:
- Looks up Total Revenue and Cost of Revenues concepts for each company
- Calculates Gross Profit for all fiscal years and quarters
- Creates Gross Profit concept if not exists (`us-gaap:GrossProfit`, path: `003`)
- Inserts values into both quarterly and annual collections

```bash
# All companies
uv run app.py --cal-gross-profit --all-companies

# Single company
uv run app.py --cal-gross-profit --cik 0000789019

# Recalculate existing values
uv run app.py --cal-gross-profit --all-companies --recalculate
uv run app.py --cal-gross-profit --cik 0000789019 --recalculate

# With verbose output
uv run app.py --cal-gross-profit --cik 0000789019 --verbose
```

### Common Options

| Option | Description |
|--------|-------------|
| `--calculate-q4` | Run Q4 calculation process |
| `--fix-cashflow` | Fix cumulative cash flow values |
| `--cal-gross-profit` | Calculate and insert Gross Profit values |
| `--all-companies` | Process all companies |
| `--cik <CIK>` | Process specific company |
| `--recalculate-q4` | Delete existing Q4 before recalculating |
| `--recalculate` | Recalculate existing values (for Gross Profit) |
| `--verbose` | Show detailed output |
| `--help` | Show help message |

### Requirements

- Must specify operation: `--calculate-q4`, `--fix-cashflow`, OR `--cal-gross-profit`
- Must specify target: `--all-companies` OR `--cik <CIK>`

## Common Company CIKs

| Company | CIK |
|---------|-----|
| Microsoft | 0000789019 |
| Apple | 0000320193 |
| Meta Platforms | 0001326801 |
| Amazon | 0001018724 |
| Alphabet | 0001652044 |

## Examples

```bash
# Calculate Q4 for Microsoft
uv run app.py --calculate-q4 --cik 0000789019

# Fix cash flows for all companies with details
uv run app.py --fix-cashflow --all-companies --verbose

# Recalculate Q4 for all companies
uv run app.py --calculate-q4 --all-companies --recalculate-q4

# Calculate Gross Profit for Microsoft
uv run app.py --cal-gross-profit --cik 0000789019

# Calculate Gross Profit for all companies with verbose output
uv run app.py --cal-gross-profit --all-companies --verbose

# Recalculate Gross Profit for Apple
uv run app.py --cal-gross-profit --cik 0000320193 --recalculate
```

## Documentation

- Full argument reference: `ARGUMENTS_REFERENCE.md`
- Cash flow fix details: `scripts/debug/CASHFLOW_FIX_DOCUMENTATION.md`
