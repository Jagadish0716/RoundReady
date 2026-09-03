# ECR module

Creates one environment-qualified private repository for the frontend, gateway, and seven backend
service images. Workers reuse their owning service image with a different command. Repositories use
AES-256 encryption, immutable tags, scan on push, and no cross-account or public repository policy.

Lifecycle rules expire untagged images after a configured age and retain a configurable count of
the newest tagged releases. Production disables force deletion and retains 30 tagged images for
rollback. Deployments should use Git SHA, release-version, or digest references—never `latest`.
Basic scan on push provides vulnerability findings but does not prove an image is safe; enhanced
Amazon Inspector scanning may be introduced with future security operations.
