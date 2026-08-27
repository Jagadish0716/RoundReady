# Event envelope

```json
{
  "event_id": "5c047243-25dc-4a22-b3ab-d772920e2322",
  "event_type": "booking.confirmed.v1",
  "event_version": 1,
  "occurred_at": "2026-08-26T05:30:00Z",
  "correlation_id": "9d09cb95-e5ef-40fd-981f-b7e398a60d31",
  "producer": "booking-service",
  "payload": {"booking_id": "9e56b58d-43c3-48bd-aa21-d82f6bdfbd74"}
}
```

Times are UTC ISO 8601 values. IDs are UUIDs. The routing key equals `event_type`.
