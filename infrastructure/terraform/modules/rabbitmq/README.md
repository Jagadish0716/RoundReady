# Amazon MQ for RabbitMQ module

Creates one private Amazon MQ RabbitMQ broker per environment. Port 5671 accepts AMQPS only from
the EKS application security group; the broker and its management interface are never public.
Application publishers and consumers continue to own exchanges, queues, routing keys, retries,
and dead-letter topology.

Terraform generates the required initial broker password and stores the username/password in
Secrets Manager. Amazon MQ requires that password in the broker resource, so it remains sensitive
Terraform state even though it is never output. Remote state must use encrypted S3 storage and
tightly restricted IAM. Future EKS workloads will receive credentials through a Pod Identity plus
CSI/external-secret design; that delivery is intentionally not implemented here.

Development uses a cost-sensitive single `mq.t3.micro`; production uses a three-node
`CLUSTER_MULTI_AZ` deployment on `mq.m5.large`. Broker class and cluster deployment dominate cost,
followed by storage, CloudWatch logs, and data transfer. Amazon MQ is chosen over an in-cluster
broker to provide managed patching, stable endpoints, and multi-AZ broker lifecycle.
