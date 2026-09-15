# Weekly availability gateway smoke — 2026-09-10

## Exact root cause and trace

Loaded GET responses contain `id`. React stores those objects as `WeeklyRuleInput[]`, but TypeScript does not strip runtime properties. The save handler spreads each object, and the API client previously serialized it unchanged. The gateway forwards `/v1/interviewers/me/availability/weekly` to interviewer-service `/v1/me/availability/weekly`. `WeeklyRuleInput` has `extra="forbid"`, so the response-only ID causes HTTP 422 before persistence. The UI searched error text for time/timezone keywords and otherwise claimed fields were highlighted without setting row errors.

The before request below was replayed through the live gateway using the existing Tuesday row and a new Monday row, following the frontend's actual serialization. It was not captured from the user's original browser session.

## Before

`PUT http://localhost:8000/v1/interviewers/me/availability/weekly`

```json
{
  "rules": [
    {
      "weekday": 1,
      "start_time": "18:00",
      "end_time": "20:00",
      "timezone": "Asia/Kolkata",
      "id": "ab7302b8-4fba-49c8-840b-7e86a79d5a6c"
    },
    {
      "weekday": 0,
      "start_time": "18:00",
      "end_time": "20:00",
      "timezone": "Asia/Kolkata"
    }
  ]
}
```

HTTP **422**; exact JSON response:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": {
      "errors": [
        {
          "type": "extra_forbidden",
          "loc": [
            "body",
            "rules",
            0,
            "id"
          ],
          "msg": "Extra inputs are not permitted"
        }
      ]
    }
  },
  "correlation_id": "64a9dd9b-1dc7-4a12-bdc8-82c63a4523d4"
}
```

The matching Tuesday row belongs to `9ec957ea-6448-400c-af74-1e6ddca191fd`, whose state is `under_review`. No verification state was changed.

## Contract verification

- Monday is integer 0; Tuesday is integer 1.
- UI clock values serialize as `18:00` and `20:00`, not AM/PM strings.
- Timezone is the separate IANA string `Asia/Kolkata`.
- Wrapper is `{ "rules": [...] }`.
- Only weekday, start_time, end_time, timezone belong in each input; response ID is forbidden. Ownership comes from authenticated identity.
- Running container and repository agree on this contract. Staleness was not the cause.
- Persistence uses timezone-free SQL TIME columns and a separate timezone string.

## Fix

Allowlist the four input fields at the frontend API boundary. Map structured backend error locations to row errors and render safe messages. Add the explicitly requested VERIFIED check before replacing weekly rows, returning `interviewer_verification_required` with HTTP 403. Only interviewer-service was rebuilt; no migration or unrelated service rebuild was needed.

## Actual browser request after fix

Chrome, en-US locale, Asia/Kolkata timezone. Used existing verified account `03a9ee0c-7f03-4969-83ea-7d7e1873264c`. Short-lived local auth-service tokens bootstrapped the browser login; login response alone was intercepted. Auth identity, profile, availability save/read/resave all went through the real gateway. No availability success response was mocked.

`PUT http://localhost:8000/v1/interviewers/me/availability/weekly`

```json
{
  "rules": [
    {
      "weekday": 1,
      "start_time": "18:00",
      "end_time": "20:00",
      "timezone": "Asia/Kolkata"
    },
    {
      "weekday": 0,
      "start_time": "18:00",
      "end_time": "20:00",
      "timezone": "Asia/Kolkata"
    }
  ]
}
```

HTTP **200**; exact JSON response:

```json
[
  {
    "weekday": 0,
    "start_time": "18:00:00",
    "end_time": "20:00:00",
    "timezone": "Asia/Kolkata",
    "id": "b487a717-fa67-4941-a1f1-ce32c8a8c3d9"
  },
  {
    "weekday": 1,
    "start_time": "18:00:00",
    "end_time": "20:00:00",
    "timezone": "Asia/Kolkata",
    "id": "474bdd58-3ac5-4c33-ad20-7b2ea33d2965"
  }
]
```

## Reload and persistence

Full reload redirects to login because the existing authentication session lives in memory. After reauthentication, the real GET returned both saved rows. A screenshot confirmed Monday and Tuesday display **06:00 PM–08:00 PM**, both **Asia/Kolkata**. Resaving the loaded rows also returned 200, proving response IDs no longer leak into subsequent saves.

Direct PostgreSQL inspection after resave:

| Weekday | Start | End | Timezone | ID |
|---|---|---|---|---|
| 0 | 18:00:00 | 20:00:00 | Asia/Kolkata | fbb8d302-47b6-4bbe-98c8-e1e7dc4d65e4 |
| 1 | 18:00:00 | 20:00:00 | Asia/Kolkata | ec3baf97-6072-49b7-bcce-81f945836772 |

No UTC shift occurred. Existing unverified account data and verification status were preserved.

## Negative checks

Real gateway: reversed range → 422; same-day overlap → 422; invalid IANA timezone → 422; unverified interviewer with valid canonical input → 403:

```json
{"error":{"code":"interviewer_verification_required","message":"Complete interviewer verification before publishing availability.","details":null},"correlation_id":"19612ea9-be64-461a-a888-1563688178ca"}
```

Browser error smoke deliberately changed outgoing availability payloads to exercise real backend rejection handling. Reversed range and timezone messages appeared beside their affected fields and at page level; list-level overlap appeared at page level. Unverified eligibility displayed the message above. Raw validation internals were not displayed.

## Validation

- Frontend interviewer-workspace suite: 29 passed, including loaded-row resave and backend error mapping regressions.
- Focused backend availability/integration selection: 2 passed; focused timezones/weekdays/rules schema selection: 5 passed (one overlapping test selection).
- Ruff lint passed; changed Python formatting passed.
- Strict MyPy: interviewer-service app/tests (19 files) and shared library/test runner (14 files) passed.
- TypeScript, ESLint, and git diff --check passed.
