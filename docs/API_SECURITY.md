# BT2C API Security Guide

## API Endpoints Security

### Authentication Endpoints

#### Create Wallet
```http
POST /api/wallet/create
Content-Type: application/json
```

**Security Measures**:
- Rate limited to 5 requests per hour
- Password strength validation
- Secure key generation
- Encrypted response

**Example Request**:
```json
{
    "password": "YourSecurePassword123!@#"
}
```

#### Validator Registration
```http
POST /api/validator/register
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Security Measures**:
- JWT authentication required
- 2FA verification required
- Node validation
- Rate limiting

### Transaction Endpoints

#### Submit Transaction
```http
POST /api/transaction
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Security Measures**:
- Transaction signing required
- Amount validation
- Double-spend prevention
- Rate limiting

**Example Request**:
```json
{
    "transaction": {
        "sender": "bt2c1234...",
        "recipient": "bt2c5678...",
        "amount": 1.0,
        "signature": "..."
    }
}
```

## Security Headers

All API responses include the following security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## Rate Limiting

### Default Limits
- General API: 100 requests per 15 minutes
- Wallet Creation: 5 requests per hour
- Validator Registration: 10 requests per day

### Response Headers
```http
X-RateLimit-Limit: <limit>
X-RateLimit-Remaining: <remaining>
X-RateLimit-Reset: <timestamp>
```

## Error Handling

### Standard Error Response
```json
{
    "error": "Error message",
    "code": "ERROR_CODE",
    "timestamp": "2025-03-07T21:52:09-06:00"
}
```

### Common Error Codes
- `AUTH_REQUIRED`: Authentication required
- `INVALID_TOKEN`: Invalid or expired token
- `RATE_LIMIT`: Rate limit exceeded
- `INVALID_INPUT`: Invalid input parameters
- `TX_INVALID`: Invalid transaction

## Best Practices

### API Authentication
1. Always use HTTPS
2. Include JWT token in Authorization header
3. Implement token refresh mechanism
4. Use short-lived tokens

### Request Validation
1. Validate input parameters
2. Check content type
3. Verify transaction signatures
4. Validate addresses

### Response Security
1. Minimize sensitive data in responses
2. Implement proper error handling
3. Use security headers
4. Rate limit responses

## Development Guidelines

### Testing Security Features
```javascript
// Example security test
describe('Wallet Creation Security', () => {
    it('should enforce password requirements', async () => {
        const response = await request(app)
            .post('/api/wallet/create')
            .send({ password: 'weak' });
        
        expect(response.status).toBe(400);
    });
});
```

### Security Middleware Usage
```javascript
// Example middleware implementation
app.use('/api/secure', 
    authenticate,
    require2FA,
    validateInput([
        body('param').isString().trim().escape()
    ])
);
```

## Monitoring and Logging

### Security Events to Monitor
1. Failed authentication attempts
2. Rate limit violations
3. Invalid transactions
4. Suspicious patterns

### Log Format
```json
{
    "timestamp": "2025-03-07T21:52:09-06:00",
    "level": "warn",
    "event": "FAILED_AUTH",
    "ip": "xxx.xxx.xxx.xxx",
    "details": "Multiple failed attempts"
}
```

## Security Checklist

### API Implementation
- [ ] Implement rate limiting
- [ ] Add input validation
- [ ] Set up security headers
- [ ] Configure error handling
- [ ] Add request logging

### Authentication
- [ ] Configure JWT
- [ ] Set up 2FA
- [ ] Implement password validation
- [ ] Add token refresh
- [ ] Set up secure sessions

### Monitoring
- [ ] Set up error tracking
- [ ] Configure access logs
- [ ] Monitor rate limits
- [ ] Track security events
- [ ] Set up alerts
