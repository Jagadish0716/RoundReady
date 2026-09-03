# Observability module

Creates one environment-qualified CloudWatch log group for future structured workload log shipping,
with bounded retention. Production also creates two reliable AWS/RDS alarms for CPU utilization and
free storage plus an SNS topic with no fabricated subscription. Alert recipients are configured by
future operations work.

This module does not install Fluent Bit, CloudWatch Agent, Container Insights, Prometheus, Grafana,
or an OTLP collector. Kubernetes deployment will later ship stdout JSON logs to this log group,
scrape private `/metrics` endpoints, and route optional application traces through an OTLP collector.
Application metrics and traces must remain non-blocking and are not exposed publicly.
