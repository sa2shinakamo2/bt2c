const { ec: EC } = require('elliptic');
const crypto = require('crypto');
const ec = new EC('secp256k1');
const fs = require('fs');
const path = require('path');

// Load BIP39 wordlist
const wordlist = require('./wordlist.json');

// Security constants
const PBKDF2_ITERATIONS = 600000; // Increased from 100000
const PBKDF2_DIGEST = 'sha512'; // Upgraded from sha256
const ENCRYPTION_ALGORITHM = 'aes-256-gcm';
const MIN_PASSWORD_LENGTH = 12;

class Wallet {
    constructor(privateKey = null) {
        this.keyPair = privateKey ? ec.keyFromPrivate(privateKey) : ec.genKeyPair();
        this.publicKey = this.keyPair.getPublic('hex');
        this.privateKey = this.keyPair.getPrivate('hex');
    }

    getAddress() {
        return crypto.createHash('ripemd160')
            .update(Buffer.from(this.publicKey, 'hex'))
            .digest('hex');
    }

    getBalance(blockchain) {
        if (!blockchain || !blockchain.chain) {
            throw new Error('Invalid blockchain object');
        }
        
        let balance = 0;
        for (const block of blockchain.chain) {
            if (block.data && block.data.validator === this.publicKey) {
                balance += block.data.reward || 0;
            }
        }
        return balance;
    }

    sign(data) {
        if (!data) {
            throw new Error('Cannot sign empty data');
        }
        return this.keyPair.sign(data).toDER('hex');
    }

    verify(data, signature) {
        if (!data || !signature) {
            throw new Error('Data and signature are required for verification');
        }
        return this.keyPair.verify(data, signature);
    }

    // Generate a backup phrase (24 words) using secure entropy
    generateBackupPhrase() {
        // Use 32 bytes (256 bits) of secure entropy
        const entropy = crypto.randomBytes(32);
        const words = [];
        
        // Use a cryptographically secure method to derive word indices
        const hash = crypto.createHash('sha256').update(entropy).digest();
        
        for (let i = 0; i < 24; i++) {
            // Use 11 bits per word as per BIP39 standard
            const position = i * 11;
            const bytePos = Math.floor(position / 8);
            const bitPos = position % 8;
            
            // Extract 11 bits for each word
            let value = 0;
            if (bitPos <= 5) {
                value = (hash[bytePos] & (0xff >> bitPos)) << (11 - (8 - bitPos));
                value |= (hash[bytePos + 1] & 0xff) >> (8 - (11 - (8 - bitPos)));
            } else {
                value = (hash[bytePos] & (0xff >> bitPos)) << (8 + (11 - (8 - bitPos)));
                value |= ((hash[bytePos + 1] & 0xff) << (11 - 8)) >> (bitPos - 5);
            }
            
            // Ensure index is within bounds
            const index = value % wordlist.length;
            words.push(wordlist[index]);
        }

        return words.join(' ');
    }

    // Encrypt wallet data with a password
    encrypt(password) {
        if (!password || typeof password !== 'string') {
            throw new Error('Password must be a non-empty string');
        }
        
        if (password.length < MIN_PASSWORD_LENGTH) {
            throw new Error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters long`);
        }

        const salt = crypto.randomBytes(32); // Increased from 16
        const key = crypto.pbkdf2Sync(password, salt, PBKDF2_ITERATIONS, 32, PBKDF2_DIGEST);
        const iv = crypto.randomBytes(16);

        const cipher = crypto.createCipheriv(ENCRYPTION_ALGORITHM, key, iv);
        
        const walletData = JSON.stringify({
            privateKey: this.privateKey,
            publicKey: this.publicKey,
            address: this.getAddress(),
            createdAt: new Date().toISOString()
        });

        let encrypted = cipher.update(walletData, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        const authTag = cipher.getAuthTag();

        return {
            encrypted,
            salt: salt.toString('hex'),
            iv: iv.toString('hex'),
            authTag: authTag.toString('hex'),
            algorithm: ENCRYPTION_ALGORITHM,
            kdf: {
                function: 'pbkdf2',
                iterations: PBKDF2_ITERATIONS,
                digest: PBKDF2_DIGEST
            }
        };
    }

    // Save encrypted wallet to file with path sanitization
    save(password, filename = 'wallet.json') {
        if (!password) {
            throw new Error('Password is required');
        }
        
        // Sanitize filename to prevent path traversal
        const sanitizedFilename = path.basename(filename.replace(/[^a-zA-Z0-9._-]/g, '_'));
        
        if (!sanitizedFilename.endsWith('.json')) {
            throw new Error('Wallet filename must have .json extension');
        }
        
        const encryptedData = this.encrypt(password);
        
        const walletDir = path.join(process.cwd(), 'wallets');
        if (!fs.existsSync(walletDir)) {
            fs.mkdirSync(walletDir, { mode: 0o700 }); // Secure permissions
        }

        const walletPath = path.join(walletDir, sanitizedFilename);
        
        // Use atomic write to prevent partial writes
        const tempPath = `${walletPath}.tmp`;
        fs.writeFileSync(
            tempPath,
            JSON.stringify(encryptedData, null, 2),
            { mode: 0o600 } // Secure file permissions
        );
        fs.renameSync(tempPath, walletPath);

        return {
            address: this.getAddress(),
            publicKey: this.publicKey,
            path: walletPath
        };
    }

    // Decrypt and load wallet from file with security checks
    static load(password, filename = 'wallet.json') {
        try {
            if (!password) {
                throw new Error('Password is required');
            }
            
            // Sanitize filename to prevent path traversal
            const sanitizedFilename = path.basename(filename.replace(/[^a-zA-Z0-9._-]/g, '_'));
            
            const walletPath = path.join(process.cwd(), 'wallets', sanitizedFilename);
            
            // Check if file exists
            if (!fs.existsSync(walletPath)) {
                throw new Error(`Wallet file not found: ${sanitizedFilename}`);
            }
            
            // Read with proper error handling
            let fileContent;
            try {
                fileContent = fs.readFileSync(walletPath, 'utf8');
            } catch (err) {
                throw new Error(`Error reading wallet file: ${err.message}`);
            }
            
            let encryptedData;
            try {
                encryptedData = JSON.parse(fileContent);
            } catch (err) {
                throw new Error(`Invalid wallet file format: ${err.message}`);
            }

            // Validate required fields
            if (!encryptedData.salt || !encryptedData.iv || !encryptedData.authTag || !encryptedData.encrypted) {
                throw new Error('Wallet file is missing required encryption data');
            }

            const salt = Buffer.from(encryptedData.salt, 'hex');
            const iv = Buffer.from(encryptedData.iv, 'hex');
            const authTag = Buffer.from(encryptedData.authTag, 'hex');
            
            // Use stored KDF parameters if available, otherwise use defaults
            const iterations = encryptedData.kdf?.iterations || PBKDF2_ITERATIONS;
            const digest = encryptedData.kdf?.digest || PBKDF2_DIGEST;
            
            const key = crypto.pbkdf2Sync(password, salt, iterations, 32, digest);
            
            const algorithm = encryptedData.algorithm || ENCRYPTION_ALGORITHM;
            const decipher = crypto.createDecipheriv(algorithm, key, iv);
            decipher.setAuthTag(authTag);

            let decrypted;
            try {
                decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
                decrypted += decipher.final('utf8');
            } catch (err) {
                throw new Error('Invalid password or corrupted wallet file');
            }

            let walletData;
            try {
                walletData = JSON.parse(decrypted);
            } catch (err) {
                throw new Error('Corrupted wallet data');
            }
            
            // Validate wallet data
            if (!walletData.privateKey || !walletData.publicKey) {
                throw new Error('Wallet data is missing required fields');
            }

            return new Wallet(walletData.privateKey);
        } catch (error) {
            console.error('Error loading wallet:', error.message);
            return null;
        }
    }
}

module.exports = { Wallet };
