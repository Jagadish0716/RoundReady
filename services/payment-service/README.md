# Payment service

The payment service owns RoundReady's ₹200 (`20000` paise, `INR`) payment records, Razorpay order
creation, verified webhooks, refunds, audit history, and transactional outbox events.

Production requires `ENVIRONMENT=production`, `PAYMENT_PROVIDER=razorpay`,
`RAZORPAY_TEST_MODE=false`, and runtime-injected `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and
`RAZORPAY_WEBHOOK_SECRET`. Configure Razorpay to deliver webhooks to the public gateway route
`POST /v1/payments/webhooks/razorpay`. Only the public key ID and order checkout metadata may be
returned to a browser; key and webhook secrets remain server-side.

Development Compose uses `PAYMENT_PROVIDER=development`. Its server-side completion endpoint is
available only in development/test and is unavailable in production. Razorpay test keys may be
used outside production with `PAYMENT_PROVIDER=razorpay` and `RAZORPAY_TEST_MODE=true`.
