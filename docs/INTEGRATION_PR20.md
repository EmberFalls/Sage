# PR #20 integration review

Base main: 62eedbc. Incoming master: 268c46c (merged PR #20).
Main is an ancestor of master. Existing F1–F3 and F4 branch commits are retained.

## Repairs

- Give login a refreshable /login URL and route using the newly authenticated user.
- Generate a server OTP session before filling farmer shortcuts.
- Cancel stale token validation when switching accounts or logging out.
- Reject malformed phones, blank names, and passwords beyond bcrypt's UTF-8 byte limit.
- Normalize duplicate email lookup, reject inactive farmers, consume OTPs atomically, and invalidate older sessions.
- Repair partial demo seeding and backend .env loading; remove unused Telegram code.
- Remove tracked runtime database; generate and seed SQLite locally.
- Show backend date-aligned stage calendar in farmer overview; identify demo review previews as unsent.
- Label illustrative hero data and role views honestly. Production RBAC and real identity verification are not implemented.
- Reports referenced an absent warning-actions endpoint before this PR. Show an explicit unavailable state rather than offering broken workflow actions. This does not complete the future warning assignment feature.
- Add GitHub Actions backend tests and frontend builds for PRs targeting main/master and pushes to main. Requiring these checks needs repository branch protection settings.

## Validation

- 29 unittest checks pass: 22 existing financial, source, calendar, and snapshot checks plus 7 new auth checks on fresh temporary databases.
- Frontend TypeScript and Vite production build pass.
- Live API checks pass for baseline, heat, bridge, reschedule, and split scenarios, including saved snapshot equality, typed contracts, and reconciled loan schedules.
- Browser checks: landing, refreshable login, officer sign-in, farmer shortcut and correct linked borrower, persisted session, scenario walkthrough and changed stage, loan outlook, reports/snapshot list.

Scope: synthetic local demo. These checks are not an exhaustive security audit or proof that future PRs will be conflict free. Model training remains paused.
