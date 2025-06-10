const crypto = require('crypto');
const { encryptWallet, decryptWallet, signTransaction } = require('./utils');

class SecureWallet {
    constructor() {
        this.type = 'BT2C';
        this.version = '1.0.0';
    }

    // Generate new wallet
    async create(password) {
        try {
            // Generate key pair
            const keyPair = crypto.generateKeyPairSync('ed25519', {
                publicKeyEncoding: { type: 'spki', format: 'pem' },
                privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
            });

            // Encrypt private key
            const encryptedPrivateKey = await encryptWallet(
                keyPair.privateKey,
                password
            );

            return {
                publicKey: keyPair.publicKey,
                encryptedPrivateKey,
                address: this.generateAddress(keyPair.publicKey)
            };
        } catch (error) {
            throw new Error('Wallet creation failed');
        }
    }

    // Generate BT2C address from public key
    generateAddress(publicKey) {
        const hash = crypto.createHash('sha256')
            .update(publicKey)
            .digest('hex');
        return `bt2c${hash.substring(0, 40)}`;
    }

    // Sign transaction
    async signTransaction(transaction, encryptedPrivateKey, password) {
        try {
            // Decrypt private key
            const privateKey = await decryptWallet(
                encryptedPrivateKey.encryptedData,
                password,
                encryptedPrivateKey.iv,
                encryptedPrivateKey.salt,
                encryptedPrivateKey.authTag
            );

            // Sign transaction
            const signature = signTransaction(transaction, privateKey);

            return {
                ...transaction,
                signature
            };
        } catch (error) {
            throw new Error('Transaction signing failed');
        }
    }

    // Validate address format
    validateAddress(address) {
        return /^bt2c[a-f0-9]{40}$/.test(address);
    }

    // Export encrypted wallet
    async exportWallet(encryptedPrivateKey, publicKey) {
        return {
            type: this.type,
            version: this.version,
            publicKey,
            encryptedPrivateKey
        };
    }

    // Import encrypted wallet
    async importWallet(walletData, password) {
        try {
            if (walletData.type !== this.type || walletData.version !== this.version) {
                throw new Error('Invalid wallet format');
            }

            // Verify wallet data
            await decryptWallet(
                walletData.encryptedPrivateKey.encryptedData,
                password,
                walletData.encryptedPrivateKey.iv,
                walletData.encryptedPrivateKey.salt,
                walletData.encryptedPrivateKey.authTag
            );

            return {
                publicKey: walletData.publicKey,
                encryptedPrivateKey: walletData.encryptedPrivateKey,
                address: this.generateAddress(walletData.publicKey)
            };
        } catch (error) {
            throw new Error('Wallet import failed');
        }
    }
}

module.exports = SecureWallet;
