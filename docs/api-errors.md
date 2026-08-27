# API error contract

All service errors use the following JSON shape and an appropriate HTTP status:

```json
{
  "error": {
    "code": "booking_not_available",
    "message": "The selected slot is no longer available",
    "details": {"slot_id": "00000000-0000-0000-0000-000000000000"}
  },
  "correlation_id": "9d09cb95-e5ef-40fd-981f-b7e398a60d31"
}
```

`code` is stable and machine-readable. `message` is safe for clients. `details` is optional,
contains no secrets, and supports field-level diagnostics. `correlation_id` is returned in
the `X-Correlation-ID` header and body.
