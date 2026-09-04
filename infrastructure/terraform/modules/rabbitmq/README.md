# Amazon MQ for RabbitMQ module

Creates one private Amazon MQ RabbitMQ broker per environment. Port 5671 accepts AMQPS only from
the EKS application security group; the broker and its management interface are never public.
Application publishers and consumers continue to own exchanges, queues, routing keys, retries,
and dead-letter topology.

Terraform generates the required initial broker password and stores the username/password plus an
application-ready `amqps://` URL in the existing Secrets Manager version. Amazon MQ requires that
password in the broker resource, so it and the derived URL remain sensitive Terraform state even
though neither is output. Remote state must use encrypted S3 storage and tightly restricted IAM.
EKS workloads receive only this existing secret through their service-specific Pod Identity and
Secrets Store CSI integration.

Development uses a cost-sensitive single `mq.m7g.medium`; production uses a three-node
`CLUSTER_MULTI_AZ` deployment on `mq.m5.large`. Broker class and cluster deployment dominate cost,
followed by storage, CloudWatch logs, and data transfer. Amazon MQ is chosen over an in-cluster
broker to provide managed patching, stable endpoints, and multi-AZ broker lifecycle.
