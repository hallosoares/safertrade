# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously at SaferTrade. If you discover a security vulnerability, please follow these steps:

### Do NOT

- ❌ Open a public GitHub issue
- ❌ Discuss the vulnerability publicly
- ❌ Exploit the vulnerability beyond what is necessary to demonstrate it

### Do

1. **Report privately** via [GitHub Security Advisories](https://github.com/felipeWandworking/safertrade/security/advisories/new)
2. **Include details**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

| Timeline | Action |
|----------|--------|
| 24 hours | Acknowledgment of your report |
| 72 hours | Initial assessment and triage |
| 7 days | Fix development begins |
| 30 days | Patch released (for critical issues) |
| 90 days | Public disclosure (coordinated) |

### Security Scope

The following are in scope for security reports:

- ✅ Detection engines
- ✅ API endpoints
- ✅ Authentication/authorization
- ✅ Data handling and storage
- ✅ Redis stream security
- ✅ Web3 integration security
- ✅ Smart contract interaction safety

### Out of Scope

- ❌ Third-party services we don't control
- ❌ Social engineering attacks
- ❌ Physical attacks
- ❌ Denial of service (unless critical)

## Security Best Practices

When using SaferTrade:

1. **Environment Variables**: Never commit `.env` files
2. **API Keys**: Rotate keys regularly
3. **Redis**: Use authentication in production
4. **Database**: Encrypt sensitive data at rest
5. **Web3 RPCs**: Use private/authenticated endpoints

## Bug Bounty Program

We are working on establishing a formal bug bounty program. Currently, we offer:

- 🏆 Public acknowledgment in CONTRIBUTORS.md
- 📜 Security researcher credit in release notes
- 🎁 SaferTrade swag (when available)

For critical vulnerabilities that could result in fund loss, contact us for potential monetary rewards.

## Contact

- **Security Team**: security@safertrade.io
- **PGP Key**: Available upon request
- **GitHub Security**: [Security Advisories](https://github.com/felipeWandworking/safertrade/security/advisories)

---

Thank you for helping keep SaferTrade and its users safe! 🛡️
