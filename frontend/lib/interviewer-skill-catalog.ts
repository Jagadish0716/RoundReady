import type { InterviewerDomain } from "@/types/interviewer";

export interface CatalogSkill {
  id: string;
  label: string;
}

export interface DomainCatalogEntry {
  id: InterviewerDomain;
  label: string;
  skills: readonly CatalogSkill[];
}

const skills = (...labels: string[]): CatalogSkill[] =>
  labels.map((label) => ({
    id: label.toLowerCase().replaceAll("/", "-").replaceAll(" ", "-"),
    label,
  }));

export const interviewerSkillCatalog: readonly DomainCatalogEntry[] = [
  {
    id: "DevOps",
    label: "DevOps",
    skills: skills(
      "Docker",
      "Kubernetes",
      "Jenkins",
      "Terraform",
      "Ansible",
      "GitHub Actions",
      "Linux",
      "CI/CD",
      "Helm",
      "Argo CD",
      "Prometheus",
    ),
  },
  {
    id: "AWS",
    label: "AWS",
    skills: skills(
      "EC2",
      "VPC",
      "IAM",
      "S3",
      "RDS",
      "Lambda",
      "ECS",
      "EKS",
      "CloudWatch",
      "Route 53",
      "API Gateway",
    ),
  },
  {
    id: "Azure",
    label: "Azure",
    skills: skills(
      "Virtual Machines",
      "Virtual Network",
      "Microsoft Entra ID",
      "Blob Storage",
      "Azure SQL",
      "Azure Functions",
      "AKS",
      "App Service",
      "Azure Monitor",
      "ARM Templates",
    ),
  },
  {
    id: "Backend",
    label: "Backend",
    skills: skills(
      "Python",
      "Java",
      "Node.js",
      "Go",
      "REST APIs",
      "GraphQL",
      "Microservices",
      "PostgreSQL",
      "Redis",
      "System Design",
    ),
  },
  {
    id: "Full Stack",
    label: "Full Stack",
    skills: skills(
      "React",
      "Next.js",
      "TypeScript",
      "Node.js",
      "Python",
      "REST APIs",
      "PostgreSQL",
      "HTML",
      "CSS",
      "System Design",
    ),
  },
  {
    id: "QA",
    label: "QA / Testing",
    skills: skills(
      "Manual Testing",
      "Selenium",
      "Cypress",
      "Playwright",
      "API Testing",
      "Performance Testing",
      "Mobile Testing",
      "Test Automation",
      "JMeter",
      "Postman",
    ),
  },
  {
    id: "Tech Support",
    label: "Technical Support",
    skills: skills(
      "Troubleshooting",
      "Linux",
      "Networking",
      "SQL",
      "Incident Management",
      "ITIL",
      "Customer Communication",
      "Monitoring",
      "Ticketing Systems",
      "Root Cause Analysis",
    ),
  },
] as const;

export const catalogForDomain = (domain: InterviewerDomain) =>
  interviewerSkillCatalog.find((entry) => entry.id === domain)!;
