#!/usr/bin/env python3
"""Fail closed unless a rendered RoundReady public Ingress is deployment-ready."""

from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REQUIRED_MARKER = "REQUIRED_"
HOST_PATTERN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
CERTIFICATE_PATTERN = re.compile(
    r"^arn:aws:acm:[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+:[0-9]{12}:certificate/[0-9a-f-]+$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    manifest = parse_args().manifest.read_text(encoding="utf-8")
    if REQUIRED_MARKER in manifest:
        raise ValueError("Production ingress contains unresolved REQUIRED_* configuration")
    resources = [item for item in yaml.safe_load_all(manifest) if isinstance(item, dict)]
    ingresses = [item for item in resources if item.get("kind") == "Ingress"]
    if len(ingresses) != 1:
        raise ValueError("Exactly one public Ingress is required")
    ingress = ingresses[0]
    rules = ingress.get("spec", {}).get("rules", [])
    hosts = [rule.get("host", "") for rule in rules]
    if len(hosts) != 2 or len(set(hosts)) != 2 or not all(HOST_PATTERN.fullmatch(h) for h in hosts):
        raise ValueError("Distinct valid frontend and API hostnames are required")
    annotations = ingress.get("metadata", {}).get("annotations", {})
    certificate = annotations.get("alb.ingress.kubernetes.io/certificate-arn", "")
    if not CERTIFICATE_PATTERN.fullmatch(certificate):
        raise ValueError("A valid explicit ACM certificate ARN is required")
    required_annotations = {
        "alb.ingress.kubernetes.io/scheme": "internet-facing",
        "alb.ingress.kubernetes.io/target-type": "ip",
        "alb.ingress.kubernetes.io/ssl-redirect": "443",
        "alb.ingress.kubernetes.io/manage-backend-security-group-rules": "true",
    }
    if any(annotations.get(key) != value for key, value in required_annotations.items()):
        raise ValueError("Ingress HTTPS, IP target, or security-group configuration is invalid")
    targets = {
        (
            path["backend"]["service"]["name"],
            path["backend"]["service"]["port"]["number"],
        )
        for rule in rules
        for path in rule["http"]["paths"]
    }
    if targets != {("frontend", 3000), ("api-gateway", 8000)}:
        raise ValueError("Public Ingress may target only frontend and api-gateway")
    application_services = [item for item in resources if item.get("kind") == "Service"]
    if any(
        service.get("spec", {}).get("type", "ClusterIP") != "ClusterIP"
        for service in application_services
    ):
        raise ValueError("All application Services must remain ClusterIP")
    policies = [item for item in resources if item.get("kind") == "NetworkPolicy"]
    expected_policies = {
        "allow-public-alb-to-frontend": ("frontend", 3000),
        "allow-public-alb-to-api-gateway": ("api-gateway", 8000),
    }
    policies_by_name = {item.get("metadata", {}).get("name"): item for item in policies}
    for name, (pod_name, port) in expected_policies.items():
        policy = policies_by_name.get(name)
        if policy is None:
            raise ValueError(f"Required NetworkPolicy is missing: {name}")
        if policy["spec"]["podSelector"] != {"matchLabels": {"app.kubernetes.io/name": pod_name}}:
            raise ValueError(f"NetworkPolicy has an invalid pod selector: {name}")
        ingress_rule = policy["spec"]["ingress"][0]
        if ingress_rule["ports"] != [{"port": port, "protocol": "TCP"}]:
            raise ValueError(f"NetworkPolicy has an invalid port: {name}")
        network = ipaddress.ip_network(ingress_rule["from"][0]["ipBlock"]["cidr"])
        if not network.is_private:
            raise ValueError("ALB source must be an explicit private VPC CIDR")
    print("Production public ingress configuration is deployment-ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
