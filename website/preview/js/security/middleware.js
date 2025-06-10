const { verifyToken, validateRequest, verify2FA } = require('./utils');
const rateLimit = require('express-rate-limit');

// Authentication middleware
const authenticate = async (req, res, next) => {
    try {
        const token = req.headers.authorization?.split(' ')[1];
        if (!token) {
            return res.status(401).json({ error: 'Authentication required' });
        }

        const decoded = verifyToken(token);
        req.user = decoded;
        next();
    } catch (error) {
        res.status(401).json({ error: 'Invalid token' });
    }
};

// 2FA verification middleware
const require2FA = async (req, res, next) => {
    try {
        const { twoFactorToken } = req.body;
        if (!twoFactorToken) {
            return res.status(401).json({ error: '2FA token required' });
        }

        const isValid = verify2FA(twoFactorToken, req.user.twoFactorSecret);
        if (!isValid) {
            return res.status(401).json({ error: 'Invalid 2FA token' });
        }

        next();
    } catch (error) {
        res.status(401).json({ error: 'Invalid 2FA token' });
    }
};

// Rate limiting for specific endpoints
const createRateLimiter = (windowMs, max, message) => {
    return rateLimit({
        windowMs,
        max,
        message: { error: message }
    });
};

// Validator node verification
const validateNode = async (req, res, next) => {
    try {
        const { validatorAddress } = req.user;
        const isValidator = await checkValidatorStatus(validatorAddress);
        if (!isValidator) {
            return res.status(403).json({ error: 'Not a valid validator node' });
        }
        next();
    } catch (error) {
        res.status(500).json({ error: 'Validator verification failed' });
    }
};

// Transaction validation middleware
const validateTransaction = async (req, res, next) => {
    try {
        const { transaction } = req.body;
        
        // Basic validation
        if (!transaction || !transaction.sender || !transaction.recipient || !transaction.amount) {
            return res.status(400).json({ error: 'Invalid transaction format' });
        }

        // Amount validation
        if (transaction.amount <= 0) {
            return res.status(400).json({ error: 'Invalid amount' });
        }

        // Signature validation
        if (!transaction.signature) {
            return res.status(400).json({ error: 'Transaction must be signed' });
        }

        // Additional validation can be added here

        next();
    } catch (error) {
        res.status(400).json({ error: 'Transaction validation failed' });
    }
};

// Request validation middleware
const validateInput = (validations) => {
    return async (req, res, next) => {
        try {
            await Promise.all(validations.map(validation => validation.run(req)));
            validateRequest(req);
            next();
        } catch (error) {
            res.status(400).json({ error: 'Invalid input' });
        }
    };
};

module.exports = {
    authenticate,
    require2FA,
    createRateLimiter,
    validateNode,
    validateTransaction,
    validateInput
};
