# BT2C (Bit2Coin)

BT2C is a Proof of Stake (PoS) cryptocurrency implementation inspired by Bitcoin. It maintains similar characteristics to Bitcoin while using an energy-efficient PoS consensus mechanism.

## Key Features

- **Consensus Mechanism**: Proof of Stake (PoS)
- **Minimum Stake**: 1 BT2C required to become a validator
- **Distribution Period**: 2 weeks
- **First Node Reward**: 100 BT2C
- **Subsequent Nodes**: 1 BT2C each
- **Block Reward**: 21 BT2C per block (halves every 4 years)
- **Total Supply**: 21 million BT2C

## Project Structure

```
bt2c/
├── website/              # Frontend website
│   ├── js/              # JavaScript files
│   ├── css/             # Stylesheets
│   └── images/          # Static images
├── api/                 # Backend API server
├── scripts/             # Deployment and utility scripts
└── migrations/          # Database migrations
```

## Getting Started

### Prerequisites
- Node.js 18.x or higher
- Python 3.8 or higher
- PostgreSQL

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bt2c.git
cd bt2c
```

2. Install backend dependencies:
```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd website
npm install
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

### Running Locally

1. Start the API server:
```bash
python api.py
```

2. Start the frontend development server:
```bash
cd website
npm start
```

## API Documentation

### Core Endpoints

- `GET /api/status`: Get blockchain network status
- `GET /api/blocks`: Get latest blocks
- `GET /api/validators`: List current validators
- `POST /api/transactions`: Create new transaction
- `GET /api/balance/{address}`: Get wallet balance

### Explorer Endpoints

- `GET /api/search`: Search blocks, transactions, or addresses
- `GET /api/stats`: Get network statistics
- `GET /api/validators/stats`: Get validator statistics

## Deployment

The project is deployed using:
- Frontend: Netlify (https://bt2c.net)
- API Server: DigitalOcean with Nginx and Let's Encrypt SSL

### Frontend Deployment
```bash
cd website
netlify deploy --prod
```

### API Server Deployment
```bash
./scripts/deploy_production.sh
```

## Security

- HTTPS enforced for all connections
- CORS configured for production domain
- Rate limiting on API endpoints
- Input validation and sanitization
- Secure session management

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- Website: https://bt2c.net
- GitHub: [Your GitHub Profile]
- Email: [Your Email]
