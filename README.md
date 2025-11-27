# Tax Fairness Coalition website

This project contains a standalone copy of the HTML-generating script originally developed in **BudgetPrimerFinal**. It generates department-style budget report HTML pages and an index page from a CSV of budget allocations.

## Contents

- `scripts/generate_departmental_reports.py` — main script that:
  - reads a budget allocations CSV
  - generates individual department HTML reports
  - generates an index HTML page with search and sort

## Setup

```bash
cd TaxFairnessCoalitionWebsite
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

## Usage

```bash
python scripts/generate_departmental_reports.py path/to/budget_allocations.csv --output-dir data/output/departmental_reports
```

The script expects the CSV schema used in the original BudgetPrimerFinal project (columns like `department_code`, `section`, `fund_type`, `amount`, etc.).

Generated HTML files will be written under the chosen `--output-dir`.
