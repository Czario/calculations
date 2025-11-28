# Q4 Financial Calculations & Cash Flow Fix

Calculate Q4 values and fix cumulative cash flow data for financial statements.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB connection details
```

## CLI Commands

### Q4 Calculation

Calculate Q4 using: `Q4 = Annual - (Q1 + Q2 + Q3)`

```bash
# All companies
python app.py --calculate-q4 --all-companies

# Single company
python app.py --calculate-q4 --cik 0000789019

# Recalculate (delete existing Q4 first)
python app.py --calculate-q4 --all-companies --recalculate-q4
python app.py --calculate-q4 --cik 0000789019 --recalculate-q4
```

### Cash Flow Fix

Convert cumulative Q2/Q3 values to quarterly: `Q2 = Q2 - Q1`, `Q3 = Q3 - Q2`

```bash
# All companies
python app.py --fix-cashflow --all-companies

# Single company
python app.py --fix-cashflow --cik 0001326801

# With verbose output
python app.py --fix-cashflow --all-companies --verbose
```

### Common Options

| Option | Description |
|--------|-------------|
| `--calculate-q4` | Run Q4 calculation process |
| `--fix-cashflow` | Fix cumulative cash flow values |
| `--all-companies` | Process all companies |
| `--cik <CIK>` | Process specific company |
| `--recalculate-q4` | Delete existing Q4 before recalculating |
| `--verbose` | Show detailed output |
| `--help` | Show help message |

### Requirements

- Must specify operation: `--calculate-q4` OR `--fix-cashflow`
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
python app.py --calculate-q4 --cik 0000789019

# Fix cash flows for all companies with details
python app.py --fix-cashflow --all-companies --verbose

# Recalculate Q4 for all companies
python app.py --calculate-q4 --all-companies --recalculate-q4
```

## Documentation

- Full argument reference: `ARGUMENTS_REFERENCE.md`
- Cash flow fix details: `scripts/debug/CASHFLOW_FIX_DOCUMENTATION.md`
