# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.x.x   | Yes       |
| < 1.0   | No        |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow responsible disclosure practices.

### Reporting Process

1. **Do not** open a public GitHub issue for security vulnerabilities
2. **Do not** discuss the vulnerability publicly before it is fixed
3. Report privately via [GitHub Security Advisories](https://github.com/hallosoares/safertrade/security/advisories/new)

### Information to Include

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested remediation (if available)

### Response Timeline

| Timeline | Action |
|----------|--------|
| 24 hours | Acknowledgment of report |
| 72 hours | Initial assessment |
| 7 days | Fix development begins |
| 30 days | Patch release for critical issues |

## Security Scope

**In scope:**
- Detection engine vulnerabilities
- Authentication and authorization issues
- Data handling and storage security
- Redis stream security
- Web3 integration security

**Out of scope:**
- Third-party service vulnerabilities
- Social engineering
- Physical security
- Denial of service (unless critical)

## Security Best Practices

When deploying SaferTrade:

1. Never commit `.env` files or credentials to version control
2. Use strong, unique passwords for Redis authentication
3. Rotate API keys regularly
4. Use authenticated RPC endpoints in production
5. Keep dependencies updated

## Contact

For security matters, use GitHub Security Advisories or contact the maintainers directly.

---

Thank you for helping keep SaferTrade secure.
