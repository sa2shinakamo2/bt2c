# BT2C Blockchain Deployment Guide

## Overview

This guide covers the deployment of the BT2C blockchain explorer in a production environment. The system uses Docker containers for easy deployment and includes monitoring, caching, and high availability features.

## Prerequisites

- Docker and Docker Compose
- 4GB RAM minimum (8GB recommended)
- 50GB storage minimum
- Linux/Unix-based OS
- Domain name (for production)
- SSL certificates

## Architecture

The system consists of several containerized services:

- BT2C Explorer (FastAPI)
- Redis Cache
- Prometheus
- Grafana
- PostgreSQL Database

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Network
NETWORK_TYPE=mainnet
API_HOST=0.0.0.0
API_PORT=8000

# Security
SECRET_KEY=your-secure-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
RATE_LIMIT_PER_MINUTE=100

# Database
DB_URL=postgresql://user:password@postgres:5432/bt2c

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=300

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

### SSL Configuration

Place SSL certificates in `./ssl/`:
```bash
./ssl/
  ├── cert.pem
  └── key.pem
```

## Deployment Steps

1. **Build and Start Services**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

2. **Initialize Database**:
   ```bash
   docker-compose exec bt2c python scripts/init_db.py
   ```

3. **Verify Deployment**:
   ```bash
   curl http://localhost:8000/health
   ```

## Monitoring Setup

1. **Access Grafana**:
   - URL: http://your-domain:3000
   - Default credentials: admin/admin

2. **Import Dashboards**:
   - Navigate to Dashboards → Import
   - Import dashboard JSONs from `monitoring/dashboards/`

3. **Configure Alerts**:
   - Set up notification channels
   - Import alert rules

## Security Considerations

1. **Firewall Rules**:
   ```bash
   # Allow only necessary ports
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 8000/tcp  # API
   ```

2. **Rate Limiting**:
   - Default: 100 requests per minute
   - Adjust in `.env` file

3. **SSL/TLS**:
   - Enable HTTPS
   - Configure SSL certificates
   - Set up automatic renewal

## Backup and Recovery

1. **Database Backup**:
   ```bash
   # Daily backup
   0 0 * * * docker-compose exec postgres pg_dump -U user bt2c > backup.sql
   ```

2. **Blockchain Data**:
   ```bash
   # Backup blockchain data
   docker-compose exec bt2c python scripts/backup.py
   ```

## Scaling

1. **Horizontal Scaling**:
   ```bash
   # Scale API servers
   docker-compose up -d --scale bt2c=3
   ```

2. **Load Balancing**:
   - Configure Nginx as reverse proxy
   - Enable sticky sessions

## Troubleshooting

1. **Check Logs**:
   ```bash
   docker-compose logs -f bt2c
   docker-compose logs -f redis
   ```

2. **Common Issues**:
   - Redis connection: Check REDIS_URL
   - Database connection: Check DB_URL
   - Memory issues: Check container limits

## Performance Tuning

1. **Redis Cache**:
   - Adjust `maxmemory` in redis.conf
   - Monitor hit/miss rates
   - Optimize TTL values

2. **Database**:
   - Index frequently queried fields
   - Optimize query patterns
   - Regular VACUUM

## Maintenance

1. **Regular Tasks**:
   - Log rotation
   - Database cleanup
   - SSL certificate renewal
   - Security updates

2. **Monitoring Checks**:
   - System resources
   - Application metrics
   - Error rates
   - Cache performance

## Support and Resources

- GitHub Repository: [BT2C Explorer](https://github.com/bt2c/explorer)
- Documentation: [Full Documentation](https://docs.bt2c.org)
- Support: [support@bt2c.org](mailto:support@bt2c.org)
