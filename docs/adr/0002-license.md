# ADR 0002: Apache License 2.0

Date: 2026-11-18 · Status: Accepted

## Decision
License the project under the Apache License 2.0 (replacing the MIT license the repository was created with). Contributions are accepted under the Developer Certificate of Origin (DCO).

## Rationale
- Permissive and open source (OSI-approved), allowing commercial use.
- Explicit patent grant and patent-retaliation clause, which MIT lacks.
- Standard for infrastructure projects (Kubernetes, Kafka, Prometheus) and widely pre-approved by enterprise legal teams.

## Consequences
- Third parties, including cloud providers, may offer the server as a service without contributing back.
- Future business model, if any, is expected to be open core: Apache 2.0 core plus separately licensed enterprise features. Source-available licenses (BSL, SSPL) are ruled out.
