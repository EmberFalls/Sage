# PhenoCredit

An offline-first prototype for FIN-03: climate-aware agricultural credit risk assessment. It demonstrates one lender workflow from crop-stage scenario assumptions through harvest timing, dated repayment cash, modeled debt pressure, and simulated interventions.

## Current scope

G0–G9 demo/rehearsal work has evidence, with real-data/model requirements still open. FastAPI seeds borrower, loan, source and scenario snapshots into SQLite; React/Vite reads registry/loan records and reopens saved requests. The single backend `evaluate_scenario` service returns eight FIN-03 input groups, baseline/stress/action, three-season debt, warnings and a cash bridge. Controls recalculate, stale responses are discarded, and reset restores baseline inputs. Backend currency uses Decimal. The report screen exports JSON/CSV and supports print-to-PDF.

**Data honesty:** borrower, loan, and repayment records are synthetic. Weather, crop calendar, yield response, price, and expenses are assumptions. NDVI and soil moisture are unavailable. The repayment estimate is simulation-conditioned and uncalibrated; it is not a real borrower default probability. Proposed actions are not applied to a real loan.

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and [DATA_SOURCES.md](DATA_SOURCES.md) for shipped feature and provenance status.

## Run locally

Requires Python 3.10+, Node.js 20+ and PowerShell 7 or Windows PowerShell. From the repository root, install dependencies once and launch both local services:

```powershell
py -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd frontend; npm ci; cd ..
./scripts/Start-PhenoCreditDemo.ps1
```

Open `http://127.0.0.1:5173/`. The API and browser app use only loopback/local fixtures. The launcher seeds two demo profiles automatically. In Scenario Lab, **Load walkthrough** applies the saved flowering-heat/split-payment scenario from `data/fixtures/judge-walkthrough.json`; **Reset scenario** restores the default borrower, date and baseline controls. Optional settings can be copied from `.env.example` to `.env`; the launcher loads the supported variables for both services. Reset/reseed the deterministic demo records with `./scripts/Reset-PhenoCreditDemo.ps1`. Stop only launcher-owned processes with `./scripts/Stop-PhenoCreditDemo.ps1`. Scenario reports stay in the local SQLite database when reseeding.

## Main API

- `GET /health`
- `GET /api/overview`
- `GET /api/borrowers`
- `GET /api/borrowers/{borrower_id}`
- `GET /api/borrowers/{borrower_id}/loan`
- `GET /api/climate?region=&crop=&as_of=`
- `POST /api/scenarios/evaluate`
- `GET /api/scenarios/{scenario_id}`
- `GET /api/scenarios?limit=50` (saved report catalog)
- `GET /api/sources`

The scenario endpoint accepts `borrower_id`, `as_of`, `overrides`, and an optional `action_id` (`none`, `reschedule_30d`, or `split_payment`). Its response includes stable input/context hashes, baseline/stress/action assessments, repayment bridge, debt cycle, warnings, source status, and claim scope.

## Limitations

G0–G9 demo/rehearsal work has runtime evidence. G8 loopback-only smoke and browser walkthroughs passed twice; G9 launch/reset scripts and handoff artifacts are in place. See the [verification report](demo/verification/REPORT.md), [offline rehearsal guide](demo/verification/REHEARSAL.md), [architecture](ARCHITECTURE.md), and [source/claim audit](DATA_SOURCES.md). G0 stack/schema and G2 real-data requirements remain partial. No real lending decision occurs.

## Verification

From `backend`, install `python -m pip install -r requirements-dev.txt`, then run `python -m unittest app.tests.test_gates -v`. With the API running, execute `python verify_live.py` and `python verify_offline.py`; the latter repeats the local acceptance smoke twice and writes run evidence. From `frontend`, run `npm ci` and `npm run build`.

On this machine the `py` launcher has no installed Python. Verification used bundled Python 3.12.14 at `C:\Users\Aaryan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`, installing dependencies with `-m pip install --target .packages -r requirements-dev.txt` from `backend`. Set `$env:PYTHONPATH=(Join-Path $PWD '.packages')` before invoking that executable for tests or Uvicorn. A normal Python virtual environment is preferred for other machines.
