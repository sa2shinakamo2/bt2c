const { ec: EC } = require('elliptic');
const crypto = require('crypto');
const ec = new EC('secp256k1');
const fs = require('fs');
const path = require('path');

// Load BIP39 wordlist
const wordlist = require('./wordlist.json');

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
        let balance = 0;
        for (const block of blockchain.chain) {
            if (block.data.validator === this.publicKey) {
                balance += block.data.reward || 0;
            }
        }
        return balance;
    }

    sign(data) {
        return this.keyPair.sign(data).toDER('hex');
    }

    verify(data, signature) {
        return this.keyPair.verify(data, signature);
    }

    // Generate a backup phrase (24 words)
    generateBackupPhrase() {
        const entropy = crypto.randomBytes(32);
        const words = [];
        
        for (let i = 0; i < 24; i++) {
            const index = entropy[i] % wordlist.length;
            words.push(wordlist[index]);
        }

        return words.join(' ');
    }

    // Encrypt wallet data with a password
    encrypt(password) {
        const salt = crypto.randomBytes(16);
        const key = crypto.pbkdf2Sync(password, salt, 100000, 32, 'sha256');
        const iv = crypto.randomBytes(16);

        const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
        
        const walletData = JSON.stringify({
            privateKey: this.privateKey,
            publicKey: this.publicKey,
            address: this.getAddress()
        });

        let encrypted = cipher.update(walletData, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        const authTag = cipher.getAuthTag();

        return {
            encrypted,
            salt: salt.toString('hex'),
            iv: iv.toString('hex'),
            authTag: authTag.toString('hex')
        };
    }

    // Save encrypted wallet to file
    save(password, filename = 'wallet.json') {
        const encryptedData = this.encrypt(password);
        
        const walletDir = path.join(process.cwd(), 'wallets');
        if (!fs.existsSync(walletDir)) {
            fs.mkdirSync(walletDir);
        }

        fs.writeFileSync(
            path.join(walletDir, filename),
            JSON.stringify(encryptedData, null, 2)
        );

        return {
            address: this.getAddress(),
            publicKey: this.publicKey
        };
    }

    // Decrypt and load wallet from file
    static load(password, filename = 'wallet.json') {
        try {
            const walletPath = path.join(process.cwd(), 'wallets', filename);
            const encryptedData = JSON.parse(fs.readFileSync(walletPath, 'utf8'));

            const salt = Buffer.from(encryptedData.salt, 'hex');
            const iv = Buffer.from(encryptedData.iv, 'hex');
            const authTag = Buffer.from(encryptedData.authTag, 'hex');
            const key = crypto.pbkdf2Sync(password, salt, 100000, 32, 'sha256');

            const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
            decipher.setAuthTag(authTag);

            let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
            decrypted += decipher.final('utf8');

            const walletData = JSON.parse(decrypted);
            return new Wallet(walletData.privateKey);
        } catch (error) {
            console.error('Error loading wallet:', error.message);
            return null;
        }
    }
}

module.exports = { Wallet };
