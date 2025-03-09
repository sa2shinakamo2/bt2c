# BT2C Best Practices Guide

## Code Quality

### Python Style Guide

1. **Code Formatting**
   ```python
   # Use black for consistent formatting
   black .
   
   # Use isort for import sorting
   isort .
   ```

2. **Type Hints**
   ```python
   from typing import List, Optional, Dict

   def get_block(height: int) -> Optional[Dict[str, any]]:
       """Get block by height."""
       pass
   ```

3. **Documentation**
   ```python
   def create_transaction(
       sender: str,
       recipient: str,
       amount: float
   ) -> Dict[str, any]:
       """Create a new transaction.
       
       Args:
           sender: Sender's address
           recipient: Recipient's address
           amount: Transaction amount
           
       Returns:
           Dictionary containing transaction details
           
       Raises:
           ValueError: If amount is negative
           InsufficientFundsError: If sender has insufficient balance
       """
       pass
   ```

### Error Handling

1. **Custom Exceptions**
   ```python
   class BT2CError(Exception):
       """Base exception for BT2C."""
       pass

   class InsufficientFundsError(BT2CError):
       """Raised when account has insufficient funds."""
       pass
   ```

2. **Error Recovery**
   ```python
   try:
       result = await operation_with_retry()
   except TemporaryError as e:
       logger.warning("operation_retry", error=str(e))
       result = await fallback_operation()
   except PermanentError as e:
       logger.error("operation_failed", error=str(e))
       raise
   ```

## Security

### Authentication

1. **Token Validation**
   ```python
   @app.middleware("http")
   async def validate_token(request: Request, call_next):
       if not is_public_endpoint(request.url.path):
           token = request.headers.get("Authorization")
           await validate_jwt_token(token)
       return await call_next(request)
   ```

2. **Password Hashing**
   ```python
   from passlib.context import CryptContext

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def hash_password(password: str) -> str:
       return pwd_context.hash(password)
   ```

### Input Validation

1. **Request Models**
   ```python
   from pydantic import BaseModel, constr, confloat

   class TransactionCreate(BaseModel):
       sender: constr(min_length=26, max_length=35)
       recipient: constr(min_length=26, max_length=35)
       amount: confloat(gt=0)
   ```

2. **Sanitization**
   ```python
   def sanitize_input(value: str) -> str:
       """Sanitize user input."""
       # Remove dangerous characters
       value = re.sub(r'[<>&;]', '', value)
       # Limit length
       return value[:MAX_LENGTH]
   ```

## Performance

### Caching Strategy

1. **Cache Keys**
   ```python
   def get_cache_key(*args, **kwargs) -> str:
       """Generate consistent cache key."""
       key_parts = [str(arg) for arg in args]
       key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
       return ":".join(key_parts)
   ```

2. **Cache Invalidation**
   ```python
   async def invalidate_related_caches(transaction: Dict):
       """Invalidate all related caches."""
       patterns = [
           f"balance:{transaction['sender']}",
           f"balance:{transaction['recipient']}",
           "network_stats"
       ]
       await cache.delete_patterns(patterns)
   ```

### Database Optimization

1. **Query Optimization**
   ```python
   # Use specific columns instead of SELECT *
   SELECT block_height, hash, timestamp 
   FROM blocks 
   WHERE height > :height 
   ORDER BY height 
   LIMIT 10
   ```

2. **Indexing**
   ```sql
   -- Create indexes for frequent queries
   CREATE INDEX idx_blocks_height ON blocks(height);
   CREATE INDEX idx_transactions_hash ON transactions(hash);
   ```

## Testing

### Unit Tests

1. **Test Structure**
   ```python
   @pytest.mark.asyncio
   async def test_transaction_creation():
       """Test transaction creation and validation."""
       # Arrange
       sender = create_test_wallet()
       recipient = create_test_wallet()
       
       # Act
       transaction = await create_transaction(
           sender.address,
           recipient.address,
           amount=1.0
       )
       
       # Assert
       assert transaction.is_valid()
       assert transaction.amount == 1.0
   ```

2. **Mocking**
   ```python
   @pytest.fixture
   def mock_blockchain():
       """Create mock blockchain for testing."""
       with patch("blockchain.BT2CBlockchain") as mock:
           mock.get_balance.return_value = 100.0
           yield mock
   ```

### Integration Tests

1. **API Tests**
   ```python
   async def test_create_transaction_api():
       """Test transaction creation via API."""
       async with AsyncClient(app=app, base_url="http://test") as client:
           response = await client.post(
               "/v1/transactions/new",
               json={
                   "sender": "test_sender",
                   "recipient": "test_recipient",
                   "amount": 1.0
               }
           )
           assert response.status_code == 200
   ```

2. **Load Tests**
   ```python
   async def test_api_performance():
       """Test API performance under load."""
       async with AsyncClient(app=app, base_url="http://test") as client:
           tasks = [
               client.get("/v1/blocks/latest")
               for _ in range(100)
           ]
           responses = await asyncio.gather(*tasks)
           assert all(r.status_code == 200 for r in responses)
   ```

## Deployment

### Container Best Practices

1. **Dockerfile**
   ```dockerfile
   # Use multi-stage builds
   FROM python:3.12-slim as builder
   COPY requirements.txt .
   RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

   FROM python:3.12-slim
   COPY --from=builder /wheels /wheels
   RUN pip install --no-cache /wheels/*
   ```

2. **Health Checks**
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
       CMD curl -f http://localhost:8000/health || exit 1
   ```

### Monitoring

1. **Metrics Collection**
   ```python
   from prometheus_client import Counter, Histogram

   REQUEST_COUNT = Counter(
       "bt2c_requests_total",
       "Total requests",
       ["endpoint", "method"]
   )

   REQUEST_LATENCY = Histogram(
       "bt2c_request_duration_seconds",
       "Request duration",
       ["endpoint"]
   )
   ```

2. **Logging**
   ```python
   import structlog

   logger = structlog.get_logger()
   logger.info(
       "transaction_created",
       hash=tx.hash,
       amount=tx.amount,
       sender=tx.sender
   )
   ```

## Maintenance

### Database Maintenance

1. **Backups**
   ```bash
   # Daily backups
   pg_dump -Fc bt2c > backup_$(date +%Y%m%d).dump
   
   # Keep last 7 days
   find . -name "backup_*.dump" -mtime +7 -delete
   ```

2. **Cleanup**
   ```sql
   -- Remove old data
   DELETE FROM transactions 
   WHERE timestamp < NOW() - INTERVAL '1 year';
   
   -- Vacuum database
   VACUUM ANALYZE;
   ```

### System Updates

1. **Dependencies**
   ```bash
   # Update dependencies
   pip-compile requirements.in
   pip-sync requirements.txt
   ```

2. **Security Updates**
   ```bash
   # Check for security vulnerabilities
   safety check
   
   # Update vulnerable packages
   pip install --upgrade vulnerable-package
   ```
