# BT2C Blockchain API Documentation

## Overview

The BT2C Blockchain API provides RESTful endpoints for interacting with the blockchain, managing transactions, querying network statistics, and managing validator operations. This API is available at `https://api.bt2c.net`.

## Base URL

```
https://api.bt2c.net
```

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
    "token_type": "bearer",
    "expires_in": 3600
}
```

### Using the Token

Include the token in the Authorization header for all authenticated requests:

```http
Authorization: Bearer your_token
```

### Token Refresh

```http
POST /auth/refresh
Authorization: Bearer your_token
```

Response:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

## API Versioning

The BT2C API uses URI versioning. The current version is `v1`.

## Endpoints

### Blockchain

#### Get Block by Height
```http
GET /v1/block/{height}
Authorization: Bearer your_token
```

Parameters:
- `height` (integer, required): The block height

Response:
```json
{
    "height": 12345,
    "hash": "000000...",
    "previous_hash": "000000...",
    "timestamp": 1645729846,
    "merkle_root": "abcdef...",
    "transactions": [
        {
            "hash": "txhash1...",
            "type": "transfer"
        },
        {
            "hash": "txhash2...",
            "type": "stake"
        }
    ],
    "validator": "bt2c_...",
    "size": 1024,
    "difficulty": 0.01,
    "nonce": 12345
}
```

#### Get Block by Hash
```http
GET /v1/block/hash/{hash}
Authorization: Bearer your_token
```

Parameters:
- `hash` (string, required): The block hash

Response: Same as Get Block by Height

#### Get Latest Blocks
```http
GET /v1/blocks/latest
Authorization: Bearer your_token
```

Query Parameters:
- `limit` (integer, optional): Number of blocks to return (default: 10, max: 100)

Response:
```json
{
    "blocks": [
        {
            "height": 12345,
            "hash": "000000...",
            "timestamp": 1645729846,
            "transaction_count": 5,
            "validator": "bt2c_..."
        }
    ],
    "pagination": {
        "total": 12345,
        "limit": 10,
        "has_more": true
    }
}
```

#### Get Transaction
```http
GET /v1/transaction/{hash}
Authorization: Bearer your_token
```

Parameters:
- `hash` (string, required): The transaction hash

Response:
```json
{
    "hash": "abcdef...",
    "sender": "bt2c_...",
    "recipient": "bt2c_...",
    "amount": 10.5,
    "fee": 0.001,
    "timestamp": 1645729846,
    "block_height": 12345,
    "confirmations": 6,
    "status": "confirmed",
    "nonce": 5,
    "signature": "sig123...",
    "memo": "Payment for services"
}
```

#### Get Transactions by Address
```http
GET /v1/address/{address}/transactions
Authorization: Bearer your_token
```

Parameters:
- `address` (string, required): The wallet address

Query Parameters:
- `limit` (integer, optional): Number of transactions to return (default: 20, max: 100)
- `offset` (integer, optional): Pagination offset
- `type` (string, optional): Filter by transaction type (transfer, stake, unstake)

Response:
```json
{
    "transactions": [
        {
            "hash": "abcdef...",
            "sender": "bt2c_...",
            "recipient": "bt2c_...",
            "amount": 10.5,
            "timestamp": 1645729846,
            "block_height": 12345,
            "type": "transfer"
        }
    ],
    "pagination": {
        "total": 156,
        "limit": 20,
        "offset": 0,
        "has_more": true
    }
}
```

### Wallet

#### Get Balance
```http
GET /v1/address/{address}/balance
Authorization: Bearer your_token
```

Parameters:
- `address` (string, required): The wallet address

Response:
```json
{
    "address": "bt2c_...",
    "balance": 100.5,
    "staked": 16.0,
    "pending_transactions": [
        {
            "hash": "txhash...",
            "amount": 5.0,
            "type": "outgoing"
        }
    ],
    "last_updated": 1645729846
}
```

#### Create Transaction
```http
POST /v1/transactions
Authorization: Bearer your_token
Content-Type: application/json

{
    "sender": "bt2c_...",
    "recipient": "bt2c_...",
    "amount": 10.5,
    "fee": 0.001,
    "nonce": 6,
    "memo": "Payment for services",
    "signature": "sig123..."
}
```

Response:
```json
{
    "transaction_hash": "abcdef...",
    "status": "pending",
    "timestamp": 1645729846,
    "estimated_confirmation_time": 300
}
```

#### Get Transaction Fee Estimate
```http
GET /v1/transactions/fee-estimate
Authorization: Bearer your_token
```

Query Parameters:
- `amount` (number, optional): Transaction amount
- `priority` (string, optional): Transaction priority (low, medium, high)

Response:
```json
{
    "fee_estimate": 0.001,
    "fee_currency": "BT2C",
    "current_network_load": "medium",
    "estimated_confirmation_time": 300
}
```

### Validators

#### Get Validators
```http
GET /v1/validators
Authorization: Bearer your_token
```

Query Parameters:
- `limit` (integer, optional): Number of validators to return (default: 20, max: 100)
- `offset` (integer, optional): Pagination offset
- `status` (string, optional): Filter by validator status (active, inactive, jailed)

Response:
```json
{
    "validators": [
        {
            "address": "bt2c_...",
            "node_name": "validator1",
            "stake": 16.0,
            "uptime": 99.9,
            "blocks_validated": 150,
            "status": "active",
            "reputation_score": 95,
            "last_block_validated": 12345,
            "commission_rate": 5.0,
            "delegated_stake": 32.0
        }
    ],
    "pagination": {
        "total": 100,
        "limit": 20,
        "offset": 0,
        "has_more": true
    }
}
```

#### Get Validator Details
```http
GET /v1/validator/{address}
Authorization: Bearer your_token
```

Parameters:
- `address` (string, required): The validator address

Response:
```json
{
    "address": "bt2c_...",
    "node_name": "validator1",
    "stake": 16.0,
    "uptime": 99.9,
    "blocks_validated": 150,
    "status": "active",
    "reputation_score": 95,
    "last_block_validated": 12345,
    "commission_rate": 5.0,
    "delegated_stake": 32.0,
    "performance_history": [
        {
            "date": "2025-03-01",
            "blocks_validated": 144,
            "uptime": 100.0
        },
        {
            "date": "2025-03-02",
            "blocks_validated": 142,
            "uptime": 98.6
        }
    ],
    "delegators": [
        {
            "address": "bt2c_...",
            "amount": 16.0
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
    "address": "bt2c_...",
    "amount": 16.0,
    "validator_address": "bt2c_...",
    "nonce": 7,
    "signature": "sig123..."
}
```

Response:
```json
{
    "status": "success",
    "stake_id": "stake123",
    "transaction_hash": "txhash...",
    "timestamp": 1645729846,
    "estimated_confirmation_time": 300
}
```

#### Unstake Tokens
```http
POST /v1/unstake
Authorization: Bearer your_token
Content-Type: application/json

{
    "address": "bt2c_...",
    "amount": 16.0,
    "validator_address": "bt2c_...",
    "nonce": 8,
    "signature": "sig123..."
}
```

Response:
```json
{
    "status": "success",
    "unstake_id": "unstake123",
    "transaction_hash": "txhash...",
    "timestamp": 1645729846,
    "estimated_completion_time": 1645730846,
    "position_in_exit_queue": 5
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
    "network_stake": 1600.0,
    "current_block_height": 12345,
    "average_block_time": 300,
    "current_difficulty": 0.01,
    "transaction_throughput": 10.5,
    "current_apy": 5.2
}
```

#### Get Network Status
```http
GET /v1/network/status
```

Response:
```json
{
    "status": "operational",
    "current_version": "1.1.0",
    "latest_block_height": 12345,
    "latest_block_time": 1645729846,
    "active_validators": 100,
    "connected_peers": 250,
    "mempool_size": 15,
    "sync_status": "synced"
}
```

## WebSocket API

BT2C also provides a WebSocket API for real-time updates.

### WebSocket Endpoint

```
wss://api.bt2c.net/ws
```

### Authentication

Send an authentication message after connecting:

```json
{
    "type": "auth",
    "token": "your_jwt_token"
}
```

### Subscribe to Events

```json
{
    "type": "subscribe",
    "channels": ["blocks", "transactions", "validator_updates"]
}
```

### Event Messages

#### New Block Event
```json
{
    "type": "block",
    "data": {
        "height": 12345,
        "hash": "000000...",
        "timestamp": 1645729846,
        "transaction_count": 5,
        "validator": "bt2c_..."
    }
}
```

#### New Transaction Event
```json
{
    "type": "transaction",
    "data": {
        "hash": "abcdef...",
        "sender": "bt2c_...",
        "recipient": "bt2c_...",
        "amount": 10.5,
        "timestamp": 1645729846,
        "status": "confirmed"
    }
}
```

## Rate Limiting

- Default: 100 requests per minute
- Authenticated users: 300 requests per minute
- WebSocket connections: 5 per IP address
- Endpoints return 429 Too Many Requests when limit exceeded
- Rate limit headers included in response:
  - `X-RateLimit-Limit`: Maximum requests allowed in the current period
  - `X-RateLimit-Remaining`: Remaining requests in the current period
  - `X-RateLimit-Reset`: Time in seconds until the rate limit resets

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

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | BAD_REQUEST | Invalid request parameters |
| 401 | UNAUTHORIZED | Authentication required |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource conflict (e.g., duplicate transaction) |
| 422 | VALIDATION_ERROR | Validation failed |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |
| 503 | SERVICE_UNAVAILABLE | Service temporarily unavailable |

## SDK Libraries

BT2C provides official SDK libraries for easy integration:

- [JavaScript/TypeScript SDK](https://github.com/sa2shinakamo2/bt2c-js)
- [Python SDK](https://github.com/sa2shinakamo2/bt2c-python)
- [Go SDK](https://github.com/sa2shinakamo2/bt2c-go)

## API Changelog

### v1.1.0 (March 2025)
- Added WebSocket support for real-time updates
- Enhanced validator statistics
- Added transaction fee estimation endpoint
- Improved rate limiting with better headers

### v1.0.0 (February 2025)
- Initial API release
