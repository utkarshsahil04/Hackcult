# Profile Accounts (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a visitor optionally sign in so the journey saved on their device is kept safely and available on any device, while everything keeps working without an account.

**Architecture:** A separate Postgres database holds user data, reached through SQLAlchemy Core from new FastAPI routes under `/api/auth` and `/api/me`. Sessions are opaque tokens in `HttpOnly` cookies, stored hashed in the database. The browser's existing journey store becomes a cache of the server's copy once signed in.

**Tech Stack:** FastAPI, SQLAlchemy 2 Core, Alembic, psycopg 3, google-auth, Next.js 16, Vitest, Playwright.

**Spec:** `backend/docs/PROFILE_ARCHITECTURE.md` (Phase 2 only). Sharing, guides, trips, badges and follows are out of scope.

## Decisions this plan assumes

The spec leaves these open. Each is the spec's recommendation or the smallest choice that fits it. **Change them here before starting.**

| Decision | Assumed | Note |
|---|---|---|
| Sign-in | Google only, verified by our API | The spec recommends Google plus email codes. Email needs a mail provider, so it follows later. `auth_identities.provider` already allows it. |
| Minimum age | Adults only, by self-declared checkbox | Avoids parental consent handling. **A lawyer must confirm this is enough.** |
| Database host | Any Postgres from `DATABASE_URL` | The spec recommends a managed service in India. |
| Sessions | A new `sessions` table | Not in the spec's data model, which leaves session storage open. |
| Recovery window | 30 days | The spec says "a short recovery window". Signing in again within it restores the account. |

**Needed from you before launch, which code can't supply:** a lawyer's review of the privacy notice text, and a process for reporting personal data breaches. Task 7 writes a first draft of the notice. Withdrawing consent is covered by deleting the account in Task 5.

## Global Constraints

- An account is never required. With accounts unavailable, every existing screen behaves exactly as it does today.
- A missing or unreachable Postgres must not stop the API starting. `.env.example` already holds a placeholder `DATABASE_URL`.
- User data never goes in the SQLite monument database, which is read-only and rebuilt from seed files.
- No raw GPS position and no visitor photo is ever stored.
- Session cookie: `raahein_session`, `HttpOnly`, `SameSite=Lax`, `Secure` outside local development. No tokens in `localStorage`.
- Store only the SHA-256 hash of a session token. A session lasts 30 days.
- Every `/api/me` query filters by the session's user id. Another user's record returns 404, never 403.
- Errors use the existing `AppError` envelope. Never log emails, tokens or names.
- Every visitor-facing string exists in English and Hindi. Interactive targets are at least 48px.
- Follow `CLAUDE.md`: smallest complete change, no unrequested options. Python 3.12. CI lints with ruff 0.17.3.
- Never commit `.env` files.

## Review Focus

1. **Stale or hand-edited device data on import:** an unknown slug or bad date is skipped and counted, and the rest still import. Pinned in Task 4.
2. **Import repeated or interrupted:** two tabs, or a dropped connection, never duplicate visits or lose the device copy. Pinned in Tasks 4 and 6.
3. **Session expires mid-use:** the visitor falls back to device mode with their journey intact and is asked to sign in again. Pinned in Task 6.
4. **Google's script blocked or unreachable:** common on patchy data and with ad blockers. The profile page still works and says sign-in is unavailable. Pinned in Task 7.
5. **Reading another person's record by guessing an id:** 404, with nothing changed. Pinned in Task 4.

---

## File Structure

| File | Responsibility |
|---|---|
| `api/app/users/tables.py` | SQLAlchemy table definitions |
| `api/app/users/db.py` | Lazy engine, `get_users_db` dependency, availability check |
| `api/app/users/sessions.py` | Create, resolve and revoke sessions; `current_user` and `require_csrf` dependencies |
| `api/app/users/visits.py` | Visit queries and the import merge |
| `api/app/services/google_auth.py` | Verify a Google ID token |
| `api/app/rate_limit.py` | In-memory rate limit shared by routes |
| `api/app/routes/auth.py` | `/api/auth/*` |
| `api/app/routes/me.py` | `/api/me*` |
| `api/alembic/`, `api/alembic.ini` | Migrations |
| `api/scripts/purge_accounts.py` | Removes accounts past the recovery window |
| `frontend/lib/account.ts` | Account API calls and journey sync |
| `frontend/components/journey/AccountPanel.tsx` | Sign-in, consent and account controls |

---

### Task 1: User database that can't break the existing app

**Files:**
- Create: `api/app/users/__init__.py`, `api/app/users/tables.py`, `api/app/users/db.py`, `api/alembic.ini`, `api/alembic/env.py`, `api/alembic/versions/0001_accounts.py`
- Modify: `api/requirements.txt`, `api/app/config.py`, `api/app/routes/health.py`, `.env.example`, `.github/workflows/ci.yml`
- Test: `api/tests/test_users_db.py`, `api/tests/test_api.py`

**Interfaces:**
- Produces: `tables.users, auth_identities, profiles, visits, consents, sessions` (`sqlalchemy.Table`); `get_users_db() -> Iterator[Connection]` raising `AppError(503, "ACCOUNTS_UNAVAILABLE", ...)`; `accounts_status() -> "ok" | "disabled" | "error"`; a test fixture `users_db` in a new `api/tests/conftest.py` that overrides `get_users_db` with a temporary migrated SQLite file.

Tables follow the spec's model, with ids as 36-character strings:
- `users`: `id`, `created_at`, `deleted_at` nullable.
- `auth_identities`: `id`, `user_id`, `provider`, `provider_subject`, with `UNIQUE (provider, provider_subject)`.
- `profiles`: `user_id` primary key, `display_name` maximum 60 characters, `home_city` nullable.
- `visits`: `id`, `user_id`, `monument_slug`, `visited_on` date, `note` nullable maximum 500 characters, `proof` default `'self'`, `created_at`, with `UNIQUE (user_id, monument_slug, visited_on)`.
- `consents`: `id`, `user_id`, `purpose`, `notice_version`, `granted_at`, `withdrawn_at` nullable.
- `sessions`: `token_hash` primary key, `user_id`, `created_at`, `expires_at`.

All child tables use `ON DELETE CASCADE` on `user_id`. Public-profile fields wait for Phase 3.

- [ ] **Step 1: Write the failing tests**

```python
def test_migration_creates_every_table(tmp_path):
    url = f"sqlite:///{tmp_path}/u.db"
    upgrade_head(url)
    assert {"users", "auth_identities", "profiles", "visits", "consents", "sessions"} <= set(inspect(create_engine(url)).get_table_names())

def test_migration_matches_table_definitions(tmp_path):
    # alembic.autogenerate.compare_metadata(...) == []

def test_same_visit_twice_is_rejected_by_the_database(users_db): ...

def test_status_is_disabled_without_a_database_url(monkeypatch):
    assert accounts_status() == "disabled"

def test_status_is_error_when_postgres_is_unreachable_and_api_still_serves(client, monkeypatch):
    # DATABASE_URL points at a closed port
    assert client.get("/api/monuments/taj-mahal").status_code == 200
    assert client.get("/api/health").json()["subsystems"]["accounts"] == "error"

def test_account_routes_return_503_when_disabled(client):
    r = client.get("/api/me")
    assert r.status_code == 503 and r.json()["error"]["code"] == "ACCOUNTS_UNAVAILABLE"
```

Add `"accounts"` to the exact key set asserted in `test_health_returns_200_with_subsystems`.

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python -m pytest api/tests/test_users_db.py -v`
Expected: FAIL on import of `app.users`.

- [ ] **Step 3: Implement**

Add `sqlalchemy>=2.0`, `alembic>=1.13` and `psycopg[binary]>=3.2` to `api/requirements.txt`. Create the engine on first use, never at import. Treat the `.env.example` placeholder as disabled by changing its `DATABASE_URL` to empty with a comment. Give `accounts_status` a 2-second connect timeout. Add a CI step that runs `pytest tests --ignore=tests/test_demo.py` from `api/`, because the API suite isn't in CI today and this code handles personal data. `test_demo.py` needs downloaded photos and has failed on `Dev` since it arrived.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest api/tests/test_users_db.py api/tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api .env.example .github/workflows/ci.yml
git commit -m "feat(accounts): add a user database that stays optional"
```

---

### Task 2: Sessions, CSRF and rate limits

**Files:**
- Create: `api/app/users/sessions.py`, `api/app/rate_limit.py`
- Modify: `api/app/main.py`, `api/app/config.py`, `api/app/routes/recognition.py`
- Test: `api/tests/test_sessions.py`

**Interfaces:**
- Consumes: `tables.sessions`, `get_users_db`.
- Produces: `create_session(conn, user_id) -> str` returning the raw token; `revoke_session(conn, token) -> None`; `current_user(request, conn) -> str` returning the user id or raising 401 `SIGN_IN_REQUIRED`; `require_csrf(request) -> None` raising 403 `CSRF_REQUIRED` unless the header `X-Raahein-Request: 1` is present; `set_session_cookie(response, token)`, `clear_session_cookie(response)`; `check_rate_limit(bucket: str, key: str, limit: int, window_seconds: int) -> None` raising 429.

- [ ] **Step 1: Write the failing tests**

```python
def test_only_the_hash_of_a_token_is_stored(users_db):
    token = create_session(users_db, user_id)
    assert token not in str(stored_row)

def test_expired_session_is_rejected(users_db): ...      # 401 SIGN_IN_REQUIRED
def test_revoked_session_is_rejected(users_db): ...
def test_session_of_a_deleted_user_is_rejected(users_db): ...
def test_cookie_flags(client):
    assert {"httponly", "samesite=lax"} <= set(cookie_attributes)
def test_writes_without_the_csrf_header_are_refused(client): ...   # 403 CSRF_REQUIRED
def test_rate_limit_blocks_then_recovers_after_the_window(monkeypatch): ...
def test_recognition_limit_still_applies(client): ...    # 30 a day, moved to the shared helper
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python -m pytest api/tests/test_sessions.py -v`
Expected: FAIL on import.

- [ ] **Step 3: Implement**

Tokens come from `secrets.token_urlsafe(32)`. The CSRF check relies on a custom header forcing a CORS preflight, so `main.py` must keep `allow_origins` to `frontend_origin` only and add `allow_credentials=True`. Add `cookie_secure: bool = True` to settings, with local development setting it false in `.env.example`. Move the store in `recognition.py` into `rate_limit.py`, with the comment `# shortcut: per-process counts, so multiple workers each count separately, upgrade to Redis when running more than one worker.`

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest api/tests/test_sessions.py api/tests/test_recognition.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api
git commit -m "feat(accounts): add secure sessions, CSRF checks and shared rate limits"
```

---

### Task 3: Google sign-in with recorded consent

**Files:**
- Create: `api/app/services/google_auth.py`, `api/app/routes/auth.py`
- Modify: `api/app/main.py`, `api/app/config.py`, `api/requirements.txt`, `.env.example`
- Test: `api/tests/test_auth.py`

**Interfaces:**
- Consumes: Task 2's session functions and `check_rate_limit`.
- Produces: `verify_google_token(token: str) -> GoogleIdentity(subject: str, name: str)`, raising `InvalidGoogleToken`. `POST /api/auth/google` with body `{id_token: str, accepted_notice_version: str, confirmed_adult: bool}` returns `{user: {display_name}, is_new: bool, restored: bool}` and sets the cookie. `POST /api/auth/logout` returns 204. Test fixtures added to `api/tests/conftest.py`, used by Tasks 4 and 5: `signed_in` (a client with a session) and `two_users` (a pair of those).

Only store the Google `sub` and name. Don't store the email, because this phase has no use for it. `NOTICE_VERSION = "2026-11"` lives in `routes/auth.py`. Limit sign-in to 20 attempts per IP per hour.

- [ ] **Step 1: Write the failing tests**

Patch `verify_google_token` in every test.

```python
def test_first_sign_in_creates_a_user_profile_and_consent(client, users_db):
    assert body["is_new"] is True and consent_row.notice_version == "2026-11"

def test_second_sign_in_finds_the_same_user(client, users_db): ...       # is_new False, one user row
def test_new_user_must_confirm_adult_and_accept_the_notice(client): ...  # 400 CONSENT_REQUIRED, nothing created
def test_returning_user_needs_no_new_consent_for_the_same_notice(client): ...
def test_invalid_token_is_401_and_creates_nothing(client): ...
def test_sign_in_within_30_days_restores_a_deleted_account(client, users_db): ...  # restored True
def test_email_is_never_stored(client, users_db): ...
def test_logout_revokes_the_session_and_clears_the_cookie(client): ...
def test_sign_in_is_rate_limited(client): ...
def test_token_is_never_logged(client, caplog): ...
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python -m pytest api/tests/test_auth.py -v`
Expected: FAIL on import.

- [ ] **Step 3: Implement**

Add `google-auth>=2.30` and `requests` to `api/requirements.txt`, and `GOOGLE_CLIENT_ID=` to `.env.example`. Use `google.oauth2.id_token.verify_oauth2_token` with the configured client id as the audience. An empty client id returns 503 `ACCOUNTS_UNAVAILABLE`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest api/tests/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api .env.example
git commit -m "feat(accounts): add Google sign-in with recorded consent"
```

---

### Task 4: Profile and visits API

**Files:**
- Create: `api/app/users/visits.py`, `api/app/routes/me.py`
- Modify: `api/app/main.py`, `api/app/schemas.py`
- Test: `api/tests/test_me.py`

**Interfaces:**
- Consumes: `current_user`, `require_csrf`, `get_users_db`, and the existing read-only `get_db` for slug checks.
- Produces: the routes below, returning `VisitOut {id, monument_slug, visited_on, note, proof}`. `POST /api/me/visits/import` takes `{name: str, visits: [{id: slug, date: "YYYY-MM-DD"}]}` (maximum 100 visits) and returns `{imported: int, already_had: int, skipped: int, visits: [VisitOut]}`.

| Route | Result |
|---|---|
| `GET /api/me` | `{display_name, home_city}` |
| `PATCH /api/me` | Updates those fields. `display_name` is 1 to 60 characters after trimming. |
| `GET /api/me/visits` | Visits, oldest first |
| `POST /api/me/visits` | 201 with the visit, 409 `VISIT_EXISTS` for the same monument and date |
| `PATCH /api/me/visits/{id}` | Changes `visited_on` or `note`, 409 on a clash |
| `DELETE /api/me/visits/{id}` | 204 |

A valid date isn't more than one day in the future, which allows for time zones, and isn't before 1900.

- [ ] **Step 1: Write the failing tests**

```python
def test_every_me_route_needs_a_session(client): ...             # 401 on all six
def test_writes_need_the_csrf_header(client): ...                # 403
def test_add_list_edit_and_delete_a_visit(signed_in): ...
def test_return_trips_on_different_dates_are_allowed(signed_in): ...
def test_same_monument_and_date_is_409(signed_in): ...
def test_unknown_monument_is_400(signed_in): ...
def test_future_date_is_400(signed_in): ...
def test_note_longer_than_500_characters_is_400(signed_in): ...

def test_another_users_visit_is_404_and_unchanged(two_users):
    assert b.patch(f"/api/me/visits/{a_visit_id}", json={"note": "x"}, headers=CSRF).status_code == 404
    assert b.delete(f"/api/me/visits/{a_visit_id}", headers=CSRF).status_code == 404
    assert a.get("/api/me/visits").json() == before

def test_import_skips_bad_rows_and_keeps_the_good_ones(signed_in):
    r = import_visits([good, {"id": "gone", "date": "2026-01-01"}, {"id": "red-fort", "date": "soon"}])
    assert (r["imported"], r["skipped"]) == (1, 2)

def test_import_twice_changes_nothing(signed_in):
    import_visits(rows); r = import_visits(rows)
    assert (r["imported"], r["already_had"]) == (0, len(rows))

def test_import_keeps_a_name_already_on_the_account(signed_in): ...
def test_import_over_100_visits_is_400(signed_in): ...
def test_import_is_rate_limited(signed_in): ...                  # 30 an hour per user
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python -m pytest api/tests/test_me.py -v`
Expected: FAIL with 404 on the routes.

- [ ] **Step 3: Implement**

Import with `INSERT ... ON CONFLICT (user_id, monument_slug, visited_on) DO NOTHING`, which both Postgres and SQLite support. Count rows affected to separate `imported` from `already_had`. Filter every query on `user_id`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest api/tests/test_me.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api
git commit -m "feat(accounts): add profile and visit routes with safe import"
```

---

### Task 5: Export and erasure

**Files:**
- Create: `api/scripts/purge_accounts.py`
- Modify: `api/app/routes/me.py`
- Test: `api/tests/test_me_privacy.py`

**Interfaces:**
- Consumes: Task 4's router and `tables`.
- Produces: `GET /api/me/export`, returning JSON `{profile, visits, consents, sign_in_methods}` with `Content-Disposition: attachment`. `DELETE /api/me` returns 204. `purge_deleted(conn, now) -> int`, which permanently removes users deleted more than 30 days ago.

- [ ] **Step 1: Write the failing tests**

```python
def test_export_holds_everything_about_this_user_only(two_users): ...
def test_export_leaves_out_session_tokens(signed_in): ...
def test_delete_ends_every_session_at_once(signed_in): ...       # 401 afterwards on all devices
def test_deleted_account_cannot_be_read(signed_in): ...
def test_purge_removes_accounts_past_30_days_and_their_rows(users_db): ...
def test_purge_keeps_accounts_inside_the_window(users_db): ...
def test_delete_needs_the_csrf_header(signed_in): ...
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python -m pytest api/tests/test_me_privacy.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement**

The purge script is a `python -m scripts.purge_accounts` command for the host's daily scheduler, and prints only a count.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest api/tests/test_me_privacy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api
git commit -m "feat(accounts): let people export and erase their data"
```

---

### Task 6: Journey sync in the browser

**Files:**
- Create: `frontend/lib/account.ts`, `frontend/lib/account.test.ts`
- Modify: `frontend/lib/api.ts`, `frontend/lib/journey.ts`

**Interfaces:**
- Consumes: Task 3 and Task 4 routes.
- Produces: `useAccount(): {status: 'unavailable' | 'signed-out' | 'signed-in', displayName?: string}`; `signIn(idToken: string, consent: {confirmedAdult: boolean}): Promise<SyncResult>`; `signOut(): Promise<void>`; `syncJourney(): Promise<SyncResult>`; `deleteAccount(): Promise<void>`; `exportAccount(): Promise<Blob>`. `SyncResult = {imported: number; skipped: number} | {error: 'offline' | 'session-expired'}`. `journey.ts` adds `replaceVisits(visits: Visit[]): void`.

Once signed in, `toggleVisit` and `setVisitDate` update the device immediately and then call the API. If that call fails, the device keeps the change and the next `syncJourney` sends it again. The UI shows one visit per monument, as Phase 1 does, using the earliest. **This refines the spec's "deletes its copy":** the browser replaces its copy with the server's list, so the page keeps working on patchy data.

- [ ] **Step 1: Write the failing tests**

Stub `fetch` in every test.

```ts
it('sends credentials and the CSRF header on account calls')
it('replaces device visits only after the server confirms the import')
it('keeps device visits when the import fails', async () => {
  // fetch rejects: result is { error: 'offline' } and visits are unchanged
})
it('falls back to signed-out and keeps visits on a 401', async () => {
  // result is { error: 'session-expired' }, useAccount reports signed-out, visits unchanged
})
it('resends a visit added while offline on the next sync')
it('reads the error code from the API envelope') // body.error.code
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pnpm -C frontend exec vitest run lib/account.test.ts`
Expected: FAIL on import.

- [ ] **Step 3: Implement**

Add `credentials: 'include'` for account calls only. Fix `apiFetch`, which reads `body.message` although the API sends `body.error.message`. Report `unavailable` when `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is unset, or when `GET /api/me` returns 503.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm -C frontend exec vitest run lib`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib
git commit -m "feat(accounts): sync the device journey with the account"
```

---

### Task 7: Account controls and same-site deployment

**Files:**
- Create: `frontend/components/journey/AccountPanel.tsx`, `frontend/app/privacy/page.tsx`, `frontend/e2e/account.spec.ts`
- Modify: `frontend/components/journey/JourneyProfile.tsx`, `frontend/next.config.mjs`, `README.md`, `backend/docs/PROFILE_ARCHITECTURE.md`, `PRODUCT.md`

**Interfaces:**
- Consumes: Task 6's `useAccount`, `signIn`, `signOut`, `exportAccount`, `deleteAccount`.
- Produces: `<AccountPanel />`, shown on `/profile` in place of the device-only notice.

`SameSite=Lax` cookies aren't sent between different sites, so production must serve the API from the web app's own address. Add a Next rewrite from `/api/:path*` to `API_ORIGIN` when that variable is set, and leave `NEXT_PUBLIC_API_URL` empty there.

`/privacy` states in plain English and Hindi what is stored (name, Google account id, visits, consents), why, that it's never sold, and how to export or erase it. It shows notice version `2026-11` and links from the consent line. Treat its text as a draft until a lawyer has reviewed it.

Copy, in English and Hindi:
- Signed out: "Keep your journey safe and see it on any device." / "अपनी यात्रा सुरक्षित रखें और किसी भी उपकरण पर देखें।"
- Consent: "I am 18 or older, and I agree to the privacy notice." / "मेरी आयु 18 वर्ष या उससे अधिक है, और मैं निजता सूचना से सहमत हूं।"
- Sign-in unavailable: "Sign-in isn't available right now. Your journey is still saved on this device." / "साइन-इन अभी उपलब्ध नहीं है। आपकी यात्रा इसी उपकरण पर सहेजी हुई है।"
- Skipped import rows: "{n} visits couldn't be added because they're no longer valid." / "{n} यात्राएं नहीं जोड़ी जा सकीं, क्योंकि वे अब मान्य नहीं हैं।"
- Delete confirmation: "Delete your account? You can restore it by signing in within 30 days. After that it's gone for good." / "क्या आप अपना खाता हटाना चाहते हैं? 30 दिनों के भीतर साइन इन करके इसे वापस पाया जा सकता है। उसके बाद यह हमेशा के लिए हट जाएगा।"

- [ ] **Step 1: Write the failing tests**

```ts
test('the journey works with accounts unavailable', ...)          // no panel controls, device notice shown, a visit saves
test('Google script failing shows the unavailable message', ...)   // route the script to abort
test('sign-in stays disabled until the consent box is ticked', ...)
test('signing in imports the device journey and reports skipped rows', ...)
test('an expired session returns to device mode without losing visits', ...)
test('delete asks first, then signs out', ...)
test('the panel works in Hindi and by keyboard', ...)
test('the consent line links to the privacy notice', ...)
```

Stub `/api/auth/*` and `/api/me*` in every test, as `flows.spec.ts` does for plans.

- [ ] **Step 2: Run them to verify they fail**

Run: `pnpm -C frontend exec playwright test e2e/account.spec.ts`
Expected: FAIL, with the panel not found.

- [ ] **Step 3: Implement**

Load Google Identity Services only when the panel is on screen, never site-wide. Style with the existing `card` and `primary-action` classes. Update `README.md` with the new settings and migration command, mark Phase 2 as built in the spec, and add the optional account to `PRODUCT.md`.

- [ ] **Step 4: Run the full verification**

Run: `.venv/Scripts/python -m pytest api backend --ignore=api/tests/test_demo.py -q`, then `pnpm -C frontend run typecheck`, `pnpm -C frontend run lint`, `pnpm -C frontend run build` and `pnpm -C frontend run test:e2e`.
Expected: all pass, with `test_demo.py` still excluded as in Task 1.

- [ ] **Step 5: Commit**

```bash
git add frontend README.md backend/docs PRODUCT.md
git commit -m "feat(accounts): add optional sign-in to the journey page"
```
