# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in BT2C, please follow these steps:

1. **Do NOT** disclose the vulnerability publicly
2. Email us at [security@bt2c.net](mailto:security@bt2c.net)
3. Include detailed information about the vulnerability
4. Allow us reasonable time to respond and fix the issue

## Security Best Practices

### Environment Variables
- Never commit `.env` files to version control
- Use `env.template` as a reference to create your `.env` file
- Keep sensitive credentials secure and rotate them regularly

### Minimum Requirements
- Stake Requirement: 1 BT2C
- Distribution Period: 2 weeks
- First Node Reward: 100 BT2C
- Subsequent Nodes: 1 BT2C each

### API Security
- All endpoints use HTTPS in production
- JWT authentication required for protected routes
- Rate limiting enabled to prevent abuse
- CORS configured for approved domains only

### Wallet Security
- Private keys are never stored in plaintext
- Use strong passwords (minimum 12 characters)
- Enable 2FA when available
- Keep recovery phrases secure and offline

### Node Security
- Use dedicated validator nodes
- Keep system and dependencies updated
- Monitor node health and performance
- Regular security audits

### Development Guidelines
1. Never commit sensitive data:
   - Private keys
   - API tokens
   - Passwords
   - Environment files
   - Configuration with credentials

2. Use secure dependencies:
   - Regular security audits
   - Keep dependencies updated
   - Use lock files for deterministic builds

3. Code Security:
   - Input validation
   - Output encoding
   - Parameterized queries
   - Security headers
   - CSP configuration

## Security Features

### Content Security Policy
- Tailwind CSS loaded from approved CDN
- Inline styles allowed for specific cases
- External resources strictly controlled

### Express.js Security
- Helmet middleware enabled
- CORS properly configured
- Rate limiting implemented
- Session security enforced

## Deployment Security

### Production Environment
- HTTPS enforced
- Secure headers configured
- Database access restricted
- Regular backups performed

### Monitoring
- System metrics tracked
- Security events logged
- Automated alerts configured
- Regular audits performed
