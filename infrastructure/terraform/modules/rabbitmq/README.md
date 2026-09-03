# Amazon MQ for RabbitMQ module

Planned interface: private broker, TLS endpoint, credentials from Secrets Manager, security
groups, maintenance/backups, and conservative broker sizing. Amazon MQ is preferred over
running RabbitMQ inside EKS because broker lifecycle and durability remain managed. The broker
must not be publicly accessible.
