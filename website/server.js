const express = require('express');
const path = require('path');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { body } = require('express-validator');
const dotenv = require('dotenv');

const { 
    authenticate, 
    require2FA, 
    createRateLimiter, 
    validateNode,
    validateTransaction,
    validateInput 
} = require('./js/security/middleware');

const SecureWallet = require('./js/security/wallet');
const securityUtils = require('./js/security/utils');

// Load environment variables
dotenv.config();

const app = express();

// Enhanced security middleware with correct CSP and CORS policies
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: [
                "'self'",
                "'unsafe-inline'",
                "https://cdn.tailwindcss.com"
            ],
            styleSrc: [
                "'self'",
                "'unsafe-inline'",
                "https://cdn.tailwindcss.com"
            ],
            imgSrc: ["'self'", "data:", "https:"],
            connectSrc: [
                "'self'",
                "https://cdn.tailwindcss.com",
                "http://localhost:8000"
            ],
            fontSrc: ["'self'", "https:", "data:"],
            objectSrc: ["'none'"],
            mediaSrc: ["'self'"],
            frameSrc: ["'none'"]
        }
    }
}));

// CORS headers middleware
app.use((req, res, next) => {
    // Handle preflight requests
    if (req.method === 'OPTIONS') {
        res.header('Access-Control-Allow-Origin', '*');
        res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
        res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
        res.header('Access-Control-Max-Age', '86400'); // 24 hours
        return res.status(204).end();
    }

    // Handle actual requests
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Cross-Origin-Resource-Policy', 'cross-origin');
    res.header('Cross-Origin-Embedder-Policy', 'credentialless');
    next();
});

app.use(express.json({ limit: '10kb' }));

// Serve static files with proper MIME types
app.use(express.static(path.join(__dirname), {
    setHeaders: (res, filePath) => {
        // Set proper content types
        if (filePath.endsWith('.css')) {
            res.setHeader('Content-Type', 'text/css');
        } else if (filePath.endsWith('.js')) {
            res.setHeader('Content-Type', 'application/javascript');
        }
        
        // Disable caching during development
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        
        // Set security headers
        res.setHeader('X-Content-Type-Options', 'nosniff');
    }
}));

// Rate limiting
const generalLimiter = createRateLimiter(
    15 * 60 * 1000, // 15 minutes
    100,
    'Too many requests from this IP, please try again later.'
);

const walletLimiter = createRateLimiter(
    60 * 60 * 1000, // 1 hour
    5,
    'Too many wallet creation attempts, please try again later.'
);

app.use('/api/', generalLimiter);
app.use('/api/wallet', walletLimiter);

// Mock data for demonstration
const mockData = {
    blocks: Array.from({ length: 100 }, (_, i) => ({
        height: 1000 - i,
        hash: `0x${Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('')}`,
        transactions: Math.floor(Math.random() * 50),
        validator: `validator${Math.floor(Math.random() * 5) + 1}`,
        timestamp: new Date(Date.now() - i * 60000).toISOString()
    })),
    transactions: Array.from({ length: 100 }, (_, i) => ({
        hash: `0x${Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('')}`,
        status: Math.random() > 0.2 ? 'confirmed' : 'pending',
        from: `0x${Array.from({ length: 40 }, () => Math.floor(Math.random() * 16).toString(16)).join('')}`,
        to: `0x${Array.from({ length: 40 }, () => Math.floor(Math.random() * 16).toString(16)).join('')}`,
        amount: (Math.random() * 100).toFixed(2),
        timestamp: new Date(Date.now() - i * 60000).toISOString()
    })),
    stats: {
        totalBlocks: 1000,
        activeValidators: 5,
        totalTransactions: 15000
    }
};

// Helper function to determine search type
function determineSearchType(query) {
    if (/^\d+$/.test(query)) {
        return 'block_height';
    } else if (/^0x[a-fA-F0-9]{40}$/.test(query)) {
        return 'address';
    } else if (/^0x[a-fA-F0-9]{64}$/.test(query)) {
        return 'transaction';
    }
    return 'unknown';
}

// Search API endpoint
app.get('/api/v1/search', (req, res) => {
    const query = req.query.q;
    if (!query) {
        return res.status(400).json({ error: 'Search query is required' });
    }

    const searchType = determineSearchType(query);
    let results = {
        type: searchType,
        data: []
    };

    switch (searchType) {
        case 'block_height':
            const height = parseInt(query);
            const block = mockData.blocks.find(b => b.height === height);
            if (block) {
                results.data = [block];
            }
            break;

        case 'address':
            const addressTxs = mockData.transactions.filter(
                tx => tx.from.toLowerCase() === query.toLowerCase() || 
                      tx.to.toLowerCase() === query.toLowerCase()
            );
            results.data = addressTxs;
            break;

        case 'transaction':
            const transaction = mockData.transactions.find(
                tx => tx.hash.toLowerCase() === query.toLowerCase()
            );
            if (transaction) {
                results.data = [transaction];
            }
            break;

        default:
            // Fuzzy search on transaction hashes and addresses
            const fuzzyResults = [
                ...mockData.transactions.filter(tx => 
                    tx.hash.toLowerCase().includes(query.toLowerCase()) ||
                    tx.from.toLowerCase().includes(query.toLowerCase()) ||
                    tx.to.toLowerCase().includes(query.toLowerCase())
                ),
                ...mockData.blocks.filter(block => 
                    block.hash.toLowerCase().includes(query.toLowerCase()) ||
                    block.validator.toLowerCase().includes(query.toLowerCase())
                )
            ].slice(0, 10);
            results.data = fuzzyResults;
    }

    res.json(results);
});

// API Routes
app.get('/api/v1/blocks/latest', (req, res) => {
    res.json(mockData.blocks);
});

app.get('/api/v1/transactions/latest', (req, res) => {
    res.json(mockData.transactions);
});

app.get('/api/v1/stats', (req, res) => {
    res.json(mockData.stats);
});

app.post('/api/v1/wallet/create', 
    validateInput([
        body('password').isLength({ min: 12 }).matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$/),
    ]),
    async (req, res) => {
        try {
            const wallet = new SecureWallet();
            const newWallet = await wallet.create(req.body.password);
            res.json(newWallet);
        } catch (error) {
            res.status(500).json({ error: 'Wallet creation failed' });
        }
    }
);

// Protected routes
app.post('/api/transaction', 
    authenticate,
    validateTransaction,
    async (req, res) => {
        try {
            // Transaction processing logic
            res.json({ success: true });
        } catch (error) {
            res.status(500).json({ error: 'Transaction failed' });
        }
    }
);

app.post('/api/validator/register',
    authenticate,
    require2FA,
    validateNode,
    async (req, res) => {
        try {
            // Validator registration logic
            res.json({ success: true });
        } catch (error) {
            res.status(500).json({ error: 'Registration failed' });
        }
    }
);

// Main routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Handle .html extensions and without
['/explorer', '/validators', '/docs', '/wallet'].forEach(route => {
    app.get(route, (req, res) => {
        res.sendFile(path.join(__dirname, `${route.substring(1)}.html`));
    });
    app.get(`${route}.html`, (req, res) => {
        res.sendFile(path.join(__dirname, `${route.substring(1)}.html`));
    });
});

// Error handling
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handling
app.use((req, res) => {
    res.status(404).sendFile(path.join(__dirname, '404.html'));
});

// Start server with HTTPS in production
if (process.env.NODE_ENV === 'production') {
    const httpsOptions = {
        key: fs.readFileSync(process.env.SSL_KEY_PATH),
        cert: fs.readFileSync(process.env.SSL_CERT_PATH)
    };
    
    https.createServer(httpsOptions, app).listen(443, () => {
        console.log('HTTPS Server running on port 443');
    });
} else {
    // Development server
    const PORT = process.env.PORT || 3000;
    app.listen(PORT, () => {
        console.log(`Development server running on port ${PORT}`);
    });
}
