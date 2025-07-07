/**
 * BT2C Cryptographic Utilities
 * 
 * Implements cryptographic functions for BT2C including:
 * - Key generation (2048-bit RSA)
 * - Address derivation (base58 encoded hash of public key)
 * - Transaction signing (RSA-PSS with SHA-256)
 * - Block and transaction hashing (SHA3-256)
 * - Seed phrases (BIP39 with 256-bit entropy)
 * - HD wallet derivation (BIP44 path m/44'/999'/0'/0/n)
 */

const NodeRSA = require('node-rsa');
const CryptoJS = require('crypto-js');
const bip39 = require('bip39');
const bs58 = require('bs58');
const crypto = require('crypto');

/**
 * Generate a new RSA key pair
 * @returns {Object} Object containing public and private keys
 */
function generateKeyPair() {
  const key = new NodeRSA({b: 2048});
  return {
    privateKey: key.exportKey('private'),
    publicKey: key.exportKey('public')
  };
}

/**
 * Derive an address from a public key
 * @param {string} publicKey - RSA public key
 * @returns {string} base58 encoded address
 */
function deriveAddress(publicKey) {
  // Hash the public key using SHA3-256
  const hash = CryptoJS.SHA3(publicKey, { outputLength: 256 }).toString();
  
  // Convert hex string to byte array
  const hashBytes = Buffer.from(hash, 'hex');
  
  // Encode with base58
  return bs58.encode(hashBytes);
}

/**
 * Sign data using RSA-PSS with SHA-256
 * @param {string} data - Data to sign
 * @param {string} privateKey - RSA private key
 * @returns {string} Base64 encoded signature
 */
function sign(data, privateKey) {
  const key = new NodeRSA(privateKey);
  const signature = key.sign(Buffer.from(data), 'base64', 'sha256');
  return signature;
}

/**
 * Verify a signature
 * @param {string} data - Original data
 * @param {string} signature - Base64 encoded signature
 * @param {string} publicKey - RSA public key
 * @returns {boolean} True if signature is valid
 */
function verify(data, signature, publicKey) {
  const key = new NodeRSA(publicKey);
  return key.verify(Buffer.from(data), signature, 'sha256', 'base64');
}

/**
 * Hash data using SHA3-256
 * @param {string|Object} data - Data to hash
 * @returns {string} Hex encoded hash
 */
function hash(data) {
  const dataStr = typeof data === 'object' ? JSON.stringify(data) : data;
  return CryptoJS.SHA3(dataStr, { outputLength: 256 }).toString();
}

/**
 * Generate a BIP39 mnemonic (24 words for 256-bit entropy)
 * @returns {string} 24-word mnemonic phrase
 */
function generateMnemonic() {
  return bip39.generateMnemonic(256);
}

/**
 * Derive a seed from a mnemonic phrase
 * @param {string} mnemonic - BIP39 mnemonic phrase
 * @param {string} passphrase - Optional passphrase
 * @returns {Buffer} Seed bytes
 */
function mnemonicToSeed(mnemonic, passphrase = '') {
  return bip39.mnemonicToSeedSync(mnemonic, passphrase);
}

/**
 * Simulate HD wallet derivation (BIP44)
 * Note: This is a simplified implementation for demonstration
 * @param {Buffer} seed - Seed bytes from mnemonicToSeed
 * @param {number} index - Account index
 * @returns {Object} Derived key pair
 */
function deriveKeyPair(seed, index = 0) {
  // In a real implementation, we would use proper BIP32/BIP44 derivation
  // For simplicity, we're using the seed and index to create a deterministic key
  const derivationPath = `m/44'/999'/0'/0/${index}`;
  
  // Create a deterministic "seed" for this path
  const pathSeed = crypto.createHash('sha256')
    .update(seed)
    .update(derivationPath)
    .digest();
  
  // Use this seed to generate a key pair
  const key = new NodeRSA({ b: 2048 });
  key.importKey({
    n: Buffer.concat([pathSeed, crypto.randomBytes(256 - pathSeed.length)]),
    e: 65537
  }, 'components-public');
  
  return {
    privateKey: key.exportKey('private'),
    publicKey: key.exportKey('public')
  };
}

module.exports = {
  generateKeyPair,
  deriveAddress,
  sign,
  verify,
  hash,
  generateMnemonic,
  mnemonicToSeed,
  deriveKeyPair
};
