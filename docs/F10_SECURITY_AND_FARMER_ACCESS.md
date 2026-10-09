# F10 security and farmer access

## Identity and session model

The API has two modes selected with `SAGE_MODE`:

- `demo` (default for local walkthroughs) seeds only synthetic borrowers, loans, and demo accounts. These legacy demo routes are public by design and must not be used to claim private account access.
- `hosted` does not seed demo borrowers or demo credentials. Set `JWT_SECRET` to a random secret of at least 32 characters and set `CORS_ALLOWED_ORIGINS` to the exact trusted web origins. Hosted mode uses short-lived signed bearer tokens (60 minutes by default), with a server-side session row for expiry and logout revocation. The browser sends the bearer in the Authorization header; the API does not use ambient cookies, so CSRF cookies are not used. Deploy behind HTTPS.

Passwords are stored as bcrypt hashes. OTP values are hashed at rest and single-use. Demo mode intentionally returns its simulated OTP on screen; hosted mode never returns it and requires a delivery integration before real enrollment can be used. Institutional roles and borrower links cannot be self-selected at registration. Hosted accounts must be provisioned by a trusted operator; the client role display is informational only.

## Farmer boundary and reports

`/api/private/farmer/*` derives the borrower link from the active server-side user record. It returns a field allowlist projection of the farmer's latest or explicitly requested immutable assessment. Unknown and cross-farmer IDs both return 404. Requests attach to the authenticated farmer, linked borrower, and assessment. `/api/private/review/*` exposes the queue only to admins or provisioned officers/leads whose server-side branch matches the borrower branch. `/api/private/officer/*` supports branch-scoped assessment evaluation, saved-result listing, reopening, and reports. JSON, CSV, and PDF exports use the same stored result, include assessment identifiers, as-of date, sources, engine version, inputs, assumptions, totals, limitations, and review status, and create an audit record. Audit rows retain actor, role, entity, action, reason, result reference, outcome, and time; they do not store passwords, tokens, or assessment financial payloads.

Farmer reports identify the result as a simulation and expose unavailable evidence. They do not make a bank decision or change a loan. The existing officer workspace and legacy demo endpoints continue to operate on seeded synthetic records in demo mode.

## Hosted rollout boundary

The current project does not yet provision production branch membership or deliver OTPs. Hosted accounts and branch IDs must be provisioned through a trusted operator process; farmer review requests persist in the app but do not notify a staffed queue. Hosted legacy portfolio routes stay closed until branch filters are added to every portfolio, object, export, and write query. Source administration is restricted to provisioned admins. A role selector in the UI is never an identity or branch claim. This is an explicit deployment gate rather than a claim that live banking is ready.
