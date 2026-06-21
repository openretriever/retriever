# Security Policy

Retriever is early-stage robotics/runtime software. Do not treat it as a safety-certified control system or security boundary.

## Reporting

Report security issues privately through the repository owner or OpenRetriever maintainers before opening a public issue.

Useful report details:

- affected package, backend, or example;
- reproduction steps;
- whether the issue involves credentials, local filesystem exposure, remote code execution, dependency supply chain, unsafe robot control, or generated artifacts.

## Secrets And Local State

Do not commit API keys, robot credentials, private endpoints, local absolute paths, logs, recordings, or unpublished data/model artifacts. Use ignored `.env` files or environment variables for local secrets.
