# F3 calibration source review: VDSA and NSS 77

Reviewed 2026-10-09. This memo records what the candidate sources can and cannot support. It is an intake checklist, not a calibration dataset or a claim that these sources are admitted to Sage.

## VDSA / ICRISAT

- Official entry points: [VDSA database](https://vdsa.icrisat.org/vdsa-database.aspx) and [micro-documentation](https://vdsa.icrisat.org/vdsa-microdoc.aspx). Candidate public extract referenced by the product plan: [Zenodo record 8224522](https://zenodo.org/records/8224522).
- Intended role: inspect agricultural household/plot economics, production-cost definitions, units, years, sampling design and geography. It may inform domain assumptions only after the exact file, codebook and license are inspected.
- Required before import: download the exact extract and record its version, source-file SHA-256, variable definitions, units, survey year, sampling weights/design, administrative identifiers and missing-value codes. Check whether the sample actually includes Pune/Maharashtra and maize, rather than inferring that from national coverage.
- Limitation: household/plot economics do not establish lender-held repayment history, delinquency, default, hidden debt or causal intervention effects. Do not link identifiable survey units to borrowers or use a distribution as an individual prediction target.

## NSS 77th round

- Official survey documentation: [MoSPI NSS 77th-round catalogue](https://microdata.gov.in/NADA/index.php/catalog/157); the plan also references the [official PIB summary](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1753856).
- Survey period: 2019 agricultural household survey. Candidate role is descriptive context or aggregate historical calibration targets after the official tables, definitions, sampling weights and release terms are inspected.
- Limitation: aggregate historical survey indicators cannot represent current individual income, a particular Pune farmer's liabilities, a bank's repayment outcomes, or default probability. Never merge survey aggregates into borrower-level credit records as if they were observations.

## Admission decision

Neither candidate is currently imported. There is no local source file, verified variable dictionary, checksum, target-geography extraction, or review of use terms in this repository. No F3 source monitor should report either source as available, and neither source may feed assessments. Record an explicit `unavailable` / `not admitted` state until the above evidence exists.

## Calibration protocol if evidence is later admitted

Keep agronomic yield calibration and credit-outcome calibration separate. Yield requires observed crop-specific outcomes, documented geography/year/units, a time-ordered holdout, leakage review and baselines. Credit calibration requires properly governed, permissioned loan outcomes and independent temporal/geographic validation. VDSA/NSS economics alone cannot satisfy the credit gate. Report sample counts, weighting, missingness and target population, and preserve the existing illustrative path if support is insufficient.
