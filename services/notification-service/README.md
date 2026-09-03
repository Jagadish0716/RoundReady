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

Development providers generate a reference without sending externally. Production uses one
provider per channel:

- Email: Resend, configured with `EMAIL_PROVIDER=resend`, `RESEND_API_BASE_URL`,
  `RESEND_API_KEY`, and `EMAIL_FROM_ADDRESS`.
- WhatsApp: Meta WhatsApp Cloud API, configured with `WHATSAPP_PROVIDER=meta`,
  `WHATSAPP_API_BASE_URL`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`,
  `WHATSAPP_TEMPLATE_NAME`, and `WHATSAPP_TEMPLATE_LANGUAGE`.

The configured Meta template must be approved and accept the rendered RoundReady message as its
single body parameter. Provider timeouts use `PROVIDER_TIMEOUT_SECONDS`. All credentials are
server-side runtime secrets; they must never be included in events, browser configuration, or
logs. Production refuses development providers or incomplete provider configuration.
