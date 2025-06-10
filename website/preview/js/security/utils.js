const crypto = require('crypto');
const argon2 = require('argon2');
const jwt = require('jsonwebtoken');
const speakeasy = require('speakeasy');
const QRCode = require('qrcode');
const { validationResult } = require('express-validator');

// Key derivation and encryption
const deriveKey = async (password, salt) => {
    try {
        const key = await argon2.hash(password, {
            type: argon2.argon2id,
            memoryCost: 2 ** 16,
            timeCost: 3,
            parallelism: 1,
            salt
        });
        return key;
    } catch (error) {
        throw new Error('Key derivation failed');
    }
};

// Wallet encryption
const encryptWallet = async (privateKey, password) => {
    try {
        const iv = crypto.randomBytes(16);
        const salt = crypto.randomBytes(16);
        const key = await deriveKey(password, salt);
        const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(key, 'hex').slice(0, 32), iv);
        
        let encryptedData = cipher.update(privateKey, 'utf8', 'hex');
        encryptedData += cipher.final('hex');
        const authTag = cipher.getAuthTag();
        
        return {
            encryptedData,
            iv: iv.toString('hex'),
            salt: salt.toString('hex'),
            authTag: authTag.toString('hex')
        };
    } catch (error) {
        throw new Error('Wallet encryption failed');
    }
};

// Wallet decryption
const decryptWallet = async (encryptedData, password, iv, salt, authTag) => {
    try {
        const key = await deriveKey(password, Buffer.from(salt, 'hex'));
        const decipher = crypto.createDecipheriv(
            'aes-256-gcm',
            Buffer.from(key, 'hex').slice(0, 32),
            Buffer.from(iv, 'hex')
        );
        decipher.setAuthTag(Buffer.from(authTag, 'hex'));
        
        let decryptedData = decipher.update(encryptedData, 'hex', 'utf8');
        decryptedData += decipher.final('utf8');
        return decryptedData;
    } catch (error) {
        throw new Error('Wallet decryption failed');
    }
};

// JWT token management
const createToken = (userId, validatorAddress) => {
    return jwt.sign(
        { 
            userId,
            validatorAddress,
            type: 'access'
        },
        process.env.JWT_SECRET,
        { expiresIn: '24h' }
    );
};

const verifyToken = (token) => {
    try {
        return jwt.verify(token, process.env.JWT_SECRET);
    } catch (error) {
        throw new Error('Invalid token');
    }
};

// 2FA
const setup2FA = async (userId) => {
    const secret = speakeasy.generateSecret({
        name: `BT2C Validator (${userId})`
    });
    const qrCode = await QRCode.toDataURL(secret.otpauth_url);
    return { 
        secret: secret.base32,
        qrCode
    };
};

const verify2FA = (token, secret) => {
    return speakeasy.totp.verify({
        secret,
        encoding: 'base32',
        token
    });
};

// Request validation
const validateRequest = (req) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        throw new Error('Invalid request parameters');
    }
};

// Transaction signing
const signTransaction = (transaction, privateKey) => {
    const message = JSON.stringify(transaction);
    const signer = crypto.createSign('SHA256');
    signer.update(message);
    return signer.sign(privateKey, 'hex');
};

const verifyTransactionSignature = (transaction, signature, publicKey) => {
    const message = JSON.stringify(transaction);
    const verifier = crypto.createVerify('SHA256');
    verifier.update(message);
    return verifier.verify(publicKey, signature, 'hex');
};

module.exports = {
    deriveKey,
    encryptWallet,
    decryptWallet,
    createToken,
    verifyToken,
    setup2FA,
    verify2FA,
    validateRequest,
    signTransaction,
    verifyTransactionSignature
};
