# Notification service

The service receives normal notification work exclusively from RabbitMQ. Run the API and consumer
as separate processes:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
python -m app.workers.consumer
```

Supported event types are bound individually by the consumer. Producers include
`recipient_email` and/or `recipient_whatsapp` in the event payload, along with the fields required
by that event's template. Provider failures are persisted and retried with exponential backoff.
Malformed broker messages use the configured RabbitMQ dead-letter exchange; unsupported events,
missing recipients, invalid template contexts, and exhausted deliveries are recorded in
`dead_letter_records`.

Development providers generate a reference without sending externally. No production email or
WhatsApp integration is enabled.
