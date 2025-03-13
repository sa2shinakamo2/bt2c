## Seed Node Configuration

### Requirements
- Docker & Docker Compose
- Nginx
- SSL/TLS certificates
- UFW (Uncomplicated Firewall)

### Ports
Seed1:
- P2P: 26656
- Prometheus: 26660
- Grafana: 3000

Seed2:
- P2P: 26658
- Prometheus: 26661
- Grafana: 3001

### Security
- SSL/TLS encryption required
- Rate limiting: 100 req/min
- UFW firewall configuration
- Self-signed certificates for development

### Setup
1. Configure firewall rules
2. Generate SSL certificates
3. Configure Nginx with provided template
4. Start Docker services

For detailed setup instructions, refer to deployment documentation.
