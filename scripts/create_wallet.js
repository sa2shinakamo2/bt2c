/**
 * BT2C Wallet Creation Script
 * 
 * This script creates a new BT2C wallet with:
 * - 24-word mnemonic phrase (BIP39)
 * - 2048-bit RSA key pair
 * - BT2C address (base58 encoded)
 * - Optional password protection
 * 
 * Usage: node create_wallet.js [--password yourpassword]
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const crypto = require('crypto');
const cryptoUtils = require('../src/crypto/utils');

// Create readline interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Ensure wallet directory exists
const homeDir = process.env.HOME || process.env.USERPROFILE;
const walletDir = path.join(homeDir, '.bt2c', 'wallets');
const configFile = path.join(homeDir, '.bt2c', 'wallet_config.json');

// Create directories if they don't exist
if (!fs.existsSync(path.join(homeDir, '.bt2c'))) {
  fs.mkdirSync(path.join(homeDir, '.bt2c'), { recursive: true });
}
if (!fs.existsSync(walletDir)) {
  fs.mkdirSync(walletDir, { recursive: true });
}

// Parse command line arguments
const args = process.argv.slice(2);
let passwordArg = null;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--password' && i + 1 < args.length) {
    passwordArg = args[i + 1];
    i++;
  }
}

/**
 * Encrypt data with a password
 * @param {string} data - Data to encrypt
 * @param {string} password - Password for encryption
 * @returns {Object} Encrypted data and IV
 */
function encrypt(data, password) {
  const iv = crypto.randomBytes(16);
  const key = crypto.scryptSync(password, 'bt2c-salt', 32);
  const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);
  
  let encrypted = cipher.update(data, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  
  return {
    encrypted,
    iv: iv.toString('hex')
  };
}

/**
 * Create a new wallet
 * @param {string} password - Optional password for encryption
 */
async function createWallet(password = null) {
  console.log('Generating new BT2C wallet...');
  
  // Generate mnemonic phrase
  const mnemonic = cryptoUtils.generateMnemonic();
  console.log('\n===== MNEMONIC PHRASE =====');
  console.log('IMPORTANT: Write down these 24 words and keep them safe!');
  console.log('They are the ONLY way to recover your wallet if lost!\n');
  console.log(mnemonic);
  console.log('\n===========================\n');
  
  // Derive seed from mnemonic
  const seed = cryptoUtils.mnemonicToSeed(mnemonic, password || '');
  
  // Derive key pair from seed
  const keyPair = cryptoUtils.deriveKeyPair(seed, 0);
  
  // Derive address from public key
  const address = 'bt2c_' + cryptoUtils.deriveAddress(keyPair.publicKey).substring(0, 26);
  
  console.log(`Wallet Address: ${address}`);
  
  // Prepare wallet data
  const walletData = {
    address,
    publicKey: keyPair.publicKey,
    privateKey: keyPair.privateKey,
    mnemonic,
    createdAt: new Date().toISOString()
  };
  
  // Save wallet data
  const walletFileName = `${address}.wallet`;
  const walletFilePath = path.join(walletDir, walletFileName);
  
  // Encrypt wallet if password provided
  if (password) {
    console.log('Encrypting wallet with password...');
    const encryptedData = encrypt(JSON.stringify(walletData), password);
    
    fs.writeFileSync(walletFilePath, JSON.stringify({
      address,
      encrypted: encryptedData.encrypted,
      iv: encryptedData.iv,
      createdAt: walletData.createdAt
    }));
    
    console.log('Wallet encrypted and saved successfully!');
  } else {
    fs.writeFileSync(walletFilePath, JSON.stringify(walletData, null, 2));
    console.log('Wallet saved successfully!');
  }
  
  // Update wallet config
  let config = {};
  if (fs.existsSync(configFile)) {
    try {
      config = JSON.parse(fs.readFileSync(configFile, 'utf8'));
    } catch (e) {
      console.log('Error reading existing config, creating new one');
      config = {};
    }
  }
  
  config.lastWallet = address;
  config.wallets = config.wallets || [];
  if (!config.wallets.includes(address)) {
    config.wallets.push(address);
  }
  
  fs.writeFileSync(configFile, JSON.stringify(config, null, 2));
  
  console.log(`\nWallet created and saved to: ${walletFilePath}`);
  console.log(`Wallet config updated at: ${configFile}`);
  console.log('\nIMPORTANT: Keep your mnemonic phrase and wallet file safe!');
  
  return address;
}

// Main function
async function main() {
  try {
    if (passwordArg !== null) {
      await createWallet(passwordArg);
      rl.close();
    } else {
      rl.question('Do you want to encrypt your wallet with a password? (y/n): ', async (answer) => {
        if (answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes') {
          rl.question('Enter password: ', async (password) => {
            await createWallet(password);
            rl.close();
          });
        } else {
          console.log('Creating unencrypted wallet (not recommended for production)');
          await createWallet();
          rl.close();
        }
      });
    }
  } catch (error) {
    console.error('Error creating wallet:', error);
    rl.close();
  }
}

main();
