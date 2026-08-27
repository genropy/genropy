# Security Policy

## Supported Versions

The Genropy team currently provides security fixes for the following
develpment branches. Released packages tag are based on the 'master'
branch, and they're usually supported up to 6 months. Released versions are
using the format 'YY.MM.DD.xxx', for easier identification of the
release date.

| Version branch | Supported          |
|----------------|--------------------|
| master         | :white_check_mark: |
| develop        | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public issues,
discussions, or pull requests.**

If you discover a security vulnerability in Genropy, report it
privately using one of the following channels:

- **Private Vulnerability Reporting**: use the "Report a
  vulnerability" button under the repository's **Security** tab
  (preferred — keeps the report and any discussion attached to the
  repo).
- **Email**: security@softwell.it 

When reporting, please include as much of the following as possible:

- A description of the vulnerability and its potential impact
- Steps to reproduce, including a minimal proof-of-concept if available
- Affected version(s) of Genropy and relevant environment details
  (Python version, database backend, deployment mode)
- Any known mitigations or workarounds

### What to expect

- **Acknowledgement**: within 3 business days of your report.
- **Status update**: within 10 business days, including an initial
  assessment (confirmed, needs more info, not applicable) and expected
  timeline.
- **Resolution**: timelines vary by severity; critical issues
  affecting authentication, authorization, session handling, SQL/HTML
  injection, or remote code execution are prioritized.
- **Disclosure**: we follow coordinated disclosure. We'll agree with
  you on a disclosure date once a fix is available, and credit
  reporters (unless anonymity is requested) in the release notes /
  advisory.

## Scope

This policy covers the Genropy framework source code in this
repository. It does **not** cover:

- Third-party packages or dependencies (report to the upstream project)
- Vulnerabilities in applications built on top of Genropy, unless the
  root cause is in the framework itself
- Issues in unsupported versions (see table above)

## Security Best Practices for Deployments

Since Genropy is often self-hosted, deployers should also:

- Keep Genropy and its dependencies up to date
- Run behind a properly configured reverse proxy / ingress with TLS
- Restrict database and admin interface access to trusted networks
- Follow the principle of least privilege for service accounts and
  database users

## Recognition

We appreciate the security research community's efforts in responsibly
disclosing issues. Reporters who follow this policy will be credited
in the corresponding security advisory, unless they prefer to remain
anonymous.
