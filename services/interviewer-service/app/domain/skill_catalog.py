SKILL_CATALOG: dict[str, dict[str, str]] = {
    "DevOps": {
        key: label
        for key, label in (
            ("docker", "Docker"),
            ("kubernetes", "Kubernetes"),
            ("jenkins", "Jenkins"),
            ("terraform", "Terraform"),
            ("ansible", "Ansible"),
            ("github-actions", "GitHub Actions"),
            ("linux", "Linux"),
            ("ci-cd", "CI/CD"),
            ("helm", "Helm"),
            ("argo-cd", "Argo CD"),
            ("prometheus", "Prometheus"),
        )
    },
    "AWS": {
        key: label
        for key, label in (
            ("ec2", "EC2"),
            ("vpc", "VPC"),
            ("iam", "IAM"),
            ("s3", "S3"),
            ("rds", "RDS"),
            ("lambda", "Lambda"),
            ("ecs", "ECS"),
            ("eks", "EKS"),
            ("cloudwatch", "CloudWatch"),
            ("route-53", "Route 53"),
            ("api-gateway", "API Gateway"),
        )
    },
    "Azure": {
        key: label
        for key, label in (
            ("virtual-machines", "Virtual Machines"),
            ("virtual-network", "Virtual Network"),
            ("microsoft-entra-id", "Microsoft Entra ID"),
            ("blob-storage", "Blob Storage"),
            ("azure-sql", "Azure SQL"),
            ("azure-functions", "Azure Functions"),
            ("aks", "AKS"),
            ("app-service", "App Service"),
            ("azure-monitor", "Azure Monitor"),
            ("arm-templates", "ARM Templates"),
        )
    },
    "Backend": {
        key: label
        for key, label in (
            ("python", "Python"),
            ("java", "Java"),
            ("node.js", "Node.js"),
            ("go", "Go"),
            ("rest-apis", "REST APIs"),
            ("graphql", "GraphQL"),
            ("microservices", "Microservices"),
            ("postgresql", "PostgreSQL"),
            ("redis", "Redis"),
            ("system-design", "System Design"),
        )
    },
    "Full Stack": {
        key: label
        for key, label in (
            ("react", "React"),
            ("next.js", "Next.js"),
            ("typescript", "TypeScript"),
            ("node.js", "Node.js"),
            ("python", "Python"),
            ("rest-apis", "REST APIs"),
            ("postgresql", "PostgreSQL"),
            ("html", "HTML"),
            ("css", "CSS"),
            ("system-design", "System Design"),
        )
    },
    "QA": {
        key: label
        for key, label in (
            ("manual-testing", "Manual Testing"),
            ("selenium", "Selenium"),
            ("cypress", "Cypress"),
            ("playwright", "Playwright"),
            ("api-testing", "API Testing"),
            ("performance-testing", "Performance Testing"),
            ("mobile-testing", "Mobile Testing"),
            ("test-automation", "Test Automation"),
            ("jmeter", "JMeter"),
            ("postman", "Postman"),
        )
    },
    "Tech Support": {
        key: label
        for key, label in (
            ("troubleshooting", "Troubleshooting"),
            ("linux", "Linux"),
            ("networking", "Networking"),
            ("sql", "SQL"),
            ("incident-management", "Incident Management"),
            ("itil", "ITIL"),
            ("customer-communication", "Customer Communication"),
            ("monitoring", "Monitoring"),
            ("ticketing-systems", "Ticketing Systems"),
            ("root-cause-analysis", "Root Cause Analysis"),
        )
    },
}
