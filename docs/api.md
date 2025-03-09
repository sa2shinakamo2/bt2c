# BT2C Blockchain API Documentation

## Overview

The BT2C Blockchain Explorer API provides endpoints for interacting with the blockchain, managing transactions, and querying network statistics.

## Authentication

The API uses JWT (JSON Web Token) authentication for secure endpoints.

### Get Token

```http
POST /auth/token
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

Response:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer"
}
```

## Endpoints

### Blockchain

#### Get Block
```http
GET /v1/block/{height}
Authorization: Bearer your_token
```

Response:
```json
{
    "height": 12345,
    "hash": "000000...",
    "previous_hash": "000000...",
    "timestamp": 1645729846,
    "transactions": [],
    "validator": "bt2c1..."
}
```

#### Get Transaction
```http
GET /v1/transaction/{hash}
Authorization: Bearer your_token
```

Response:
```json
{
    "hash": "abcdef...",
    "sender": "bt2c1...",
    "recipient": "bt2c1...",
    "amount": 10.5,
    "timestamp": 1645729846,
    "block_height": 12345
}
```

### Wallet

#### Get Balance
```http
GET /v1/balance/{address}
Authorization: Bearer your_token
```

Response:
```json
{
    "address": "bt2c1...",
    "balance": 100.5,
    "pending_transactions": []
}
```

#### Create Transaction
```http
POST /v1/transactions/new
Authorization: Bearer your_token
Content-Type: application/json

{
    "sender": "bt2c1...",
    "recipient": "bt2c1...",
    "amount": 10.5
}
```

Response:
```json
{
    "transaction_hash": "abcdef...",
    "status": "pending"
}
```

### Validators

#### Get Validators
```http
GET /v1/validators
Authorization: Bearer your_token
```

Response:
```json
{
    "validators": [
        {
            "address": "bt2c1...",
            "stake": 16.0,
            "uptime": 99.9,
            "blocks_validated": 150
        }
    ]
}
```

#### Stake Tokens
```http
POST /v1/stake
Authorization: Bearer your_token
Content-Type: application/json

{
    "address": "bt2c1...",
    "amount": 16.0
}
```

Response:
```json
{
    "status": "success",
    "stake_id": "stake123"
}
```

### Network

#### Get Network Stats
```http
GET /v1/network/stats
Authorization: Bearer your_token
```

Response:
```json
{
    "total_supply": 21000000,
    "circulating_supply": 18500000,
    "total_transactions": 1234567,
    "total_blocks": 54321,
    "active_validators": 100,
    "network_stake": 1600.0
}
```

## Rate Limiting

- Default: 100 requests per minute
- Endpoints return 429 Too Many Requests when limit exceeded
- Rate limit headers included in response:
  - X-RateLimit-Limit
  - X-RateLimit-Remaining
  - X-RateLimit-Reset

## Error Handling

### Error Response Format
```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Error description",
        "details": {}
    }
}
```

### Common Error Codes

- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Too Many Requests
- `500`: Internal Server Error

## Websocket API

### Subscribe to Updates
```javascript
ws://your-domain/ws/updates

// Message format
{
    "type": "subscribe",
    "channels": ["blocks", "transactions"]
}
```

### Event Types

1. New Block:
```json
{
    "type": "block",
    "data": {
        "height": 12345,
        "hash": "000000..."
    }
}
```

2. New Transaction:
```json
{
    "type": "transaction",
    "data": {
        "hash": "abcdef...",
        "status": "confirmed"
    }
}
```

## Best Practices

1. **Error Handling**:
   - Always check response status codes
   - Implement exponential backoff for retries
   - Handle rate limiting appropriately

2. **Authentication**:
   - Store tokens securely
   - Refresh tokens before expiration
   - Never expose tokens in client-side code

3. **Performance**:
   - Use websockets for real-time updates
   - Cache responses when appropriate
   - Batch requests when possible

## SDK Examples

### Python
```python
from bt2c_client import BT2CClient

client = BT2CClient(api_key="your_api_key")

# Get block
block = await client.get_block(12345)

# Create transaction
tx = await client.create_transaction(
    sender="bt2c1...",
    recipient="bt2c1...",
    amount=10.5
)
```

### JavaScript
```javascript
import { BT2CClient } from 'bt2c-client';

const client = new BT2CClient({ apiKey: 'your_api_key' });

// Get block
const block = await client.getBlock(12345);

// Create transaction
const tx = await client.createTransaction({
    sender: 'bt2c1...',
    recipient: 'bt2c1...',
    amount: 10.5
});
```

## Support

For API support:
- Email: api@bt2c.org
- Discord: [BT2C Discord](https://discord.gg/bt2c)
- GitHub Issues: [BT2C Repository](https://github.com/bt2c/explorer)
