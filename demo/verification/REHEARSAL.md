# Offline demo rehearsal (about 3 minutes)

Use the exact input values below if you want the saved evidence numbers to match. Everything is local; no external data service is called.

## Start

From the repository root, start both loopback services with one command after installing the pinned dependencies shown in `README.md`:

```powershell
./scripts/Start-PhenoCreditDemo.ps1
```

The app seeds its two synthetic borrowers on API startup. To reseed them without restarting the services, run `./scripts/Reset-PhenoCreditDemo.ps1`. To stop only processes started by the launcher, run `./scripts/Stop-PhenoCreditDemo.ps1`. Logs and owned process IDs are written under ignored `demo/run/`.

Terminal 1, from `backend`:

```powershell
$env:PYTHONPATH = (Join-Path $PWD '.packages')
& 'C:\Users\Aaryan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, from `frontend`:

```powershell
npm run dev -- --host 127.0.0.1
```

Open the local Vite address. For a normal Python install, activate its environment and install `backend/requirements.txt`; the bundled interpreter path above is specific to this development machine.

## Walkthrough

1. **Overview → Borrowers:** show two clearly synthetic profiles. Search `Pune`, open Demo Farmer 002, then visit Climate Intelligence to show dated assumed stages and explicit NDVI/soil gaps.
2. **Scenario Lab:** choose Demo Farmer 001 and click **Load walkthrough**. This loads the checked request in `data/fixtures/judge-walkthrough.json`: heatwave **4 days**, exposed growth stage **flowering**, and action **split payment**. Expected outputs: stress sale Nov 9, cash before due ₹73,000, first due gap ₹52,365.48; split installments ₹63,622.98 and ₹64,510.65. The fixed baseline remains unchanged.
3. Set stage to **harvest**, crop price change to **−80%**, and informal bridge borrowing to **₹150,000**. Explain that the bridge pays the bank in this example while total informal debt grows over three seasons. Warnings are simulated ledger rules, not hidden-debt detection.
4. Choose **Reset scenario**. The default borrower/date and baseline values return. Visit **Intervention Center** and compare +30-day and split-payment options; both are proposals requiring lender review.
5. Visit **Watchlist & Reports**. Download JSON or bridge CSV; use Print / save PDF for the summary. Reopen a saved scenario and verify its borrower, shock controls and action return. Open **Farmer view** and explain the due-date gap as illustrative.

## Final check

From `backend`, run `python -m unittest app.tests.test_gates -v` and `python verify_live.py`. From `frontend`, run `npm run build`. Keep claim labels visible: financial profiles are synthetic; weather/calendar/yield/price are assumptions; repayment frequencies are uncalibrated; no loan is changed.

For the local-only acceptance sequence (health → seed → borrowers and sources → cloned baseline → heat/stage sensitivity → bridge/debt → interventions → saved snapshot and loan schedule → climate availability labels), run `python verify_offline.py` from `backend` while the API is running. It executes the smoke twice, refuses non-loopback API URLs, makes no external requests and writes one evidence JSON per pass under `demo/verification/`.

## G8 rehearsal record (2026-10-09)

Two local-only smoke passes and two browser walkthroughs completed. Both browser passes covered overview/watchlist, borrower registry, climate provenance, a four-day heat scenario with split payment, intervention eligibility, JSON/CSV report controls, snapshot reopen and Farmer view. Both selected an eligible pre-due-date snapshot and showed assumed/unavailable source labels. The clean-start `Load walkthrough` action and `Reset scenario` action were also exercised; the walkthrough values are checked against the saved request fixture. See `offline-smoke-pass-1.json`, `offline-smoke-pass-2.json`, `browser-g8-rehearsal.jpg`, and `data/fixtures/judge-walkthrough.json`.

Launcher start/stop was exercised on alternate loopback ports and cleaned up its own processes. `npm run build` passed and all 18 backend gate tests passed. Print/PDF was not rendered; no video was recorded.
