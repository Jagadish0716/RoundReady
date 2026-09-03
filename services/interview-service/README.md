# Interview service

The interview service owns interview sessions, attendance, rubrics, feedback, and LiveKit room
access. Room names are derived server-side from the booking ID and reused safely. Candidate and
interviewer join requests are ownership-checked against the persisted session before a token is
issued.

Production requires `ENVIRONMENT=production`, `VIDEO_PROVIDER=livekit`,
`LIVEKIT_TEST_MODE=false`, and runtime-injected `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and
`LIVEKIT_API_SECRET`. The URL must be HTTPS/WSS and non-local. Participant tokens are generated
server-side, scoped to one assigned room, grant only join/publish/subscribe/data permissions,
and expire after `PARTICIPANT_TOKEN_TTL_SECONDS` (60–900 seconds). Tokens and API credentials are
not persisted or logged.

Development Compose uses `VIDEO_PROVIDER=development` and performs no LiveKit network call. A
LiveKit test deployment may be used outside production with `VIDEO_PROVIDER=livekit` and
`LIVEKIT_TEST_MODE=true`. Development/test providers cannot activate in production. Recording,
egress, transcription, and storage are disabled and are not implemented.
