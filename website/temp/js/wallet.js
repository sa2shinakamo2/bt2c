// Import ethers from CDN (since we're using it client-side)
import { ethers } from "https://cdn.ethers.io/lib/ethers-5.7.esm.min.js";

// Constants
const MIN_PASSWORD_LENGTH = 12;
const MAX_LOGIN_ATTEMPTS = 3;
let loginAttempts = 0;

// Password strength checker
function checkPasswordStrength(password) {
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    const strength = {
        isStrong: false,
        message: []
    };

    if (password.length < MIN_PASSWORD_LENGTH) {
        strength.message.push(`Password must be at least ${MIN_PASSWORD_LENGTH} characters long`);
    }
    if (!hasUpperCase) strength.message.push("Must contain uppercase letters");
    if (!hasLowerCase) strength.message.push("Must contain lowercase letters");
    if (!hasNumbers) strength.message.push("Must contain numbers");
    if (!hasSpecialChar) strength.message.push("Must contain special characters");

    strength.isStrong = password.length >= MIN_PASSWORD_LENGTH && 
                       hasUpperCase && hasLowerCase && 
                       hasNumbers && hasSpecialChar;

    return strength;
}

// Secure wallet generation
async function createWallet() {
    try {
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;

        // Check password match
        if (password !== confirmPassword) {
            throw new Error('Passwords do not match');
        }

        // Check password strength
        const passwordStrength = checkPasswordStrength(password);
        if (!passwordStrength.isStrong) {
            throw new Error(`Weak password: ${passwordStrength.message.join(', ')}`);
        }

        // Check login attempts
        if (loginAttempts >= MAX_LOGIN_ATTEMPTS) {
            const waitTime = 30; // 30 seconds timeout
            throw new Error(`Too many attempts. Please wait ${waitTime} seconds`);
        }

        // Generate wallet using ethers.js
        const wallet = ethers.Wallet.createRandom();
        
        // Encrypt wallet with password
        const encryptedWallet = await wallet.encrypt(password, {
            scrypt: {
                N: 131072, // Higher number means more secure but slower
            }
        });

        // Store encrypted wallet in localStorage (you might want to use a more secure storage in production)
        localStorage.setItem('encryptedWallet', encryptedWallet);

        // Show wallet info
        document.getElementById('wallet-info').classList.remove('hidden');
        document.getElementById('recovery-phrase').textContent = wallet.mnemonic.phrase;
        document.getElementById('wallet-address').value = wallet.address;

        // Add warning message about mnemonic phrase
        const warningDiv = document.createElement('div');
        warningDiv.className = 'mt-4 p-4 bg-red-100 text-red-700 rounded-md';
        warningDiv.innerHTML = `
            <strong>⚠️ WARNING:</strong>
            <ul class="list-disc ml-4 mt-2">
                <li>Save this recovery phrase in a secure location</li>
                <li>Never share it with anyone</li>
                <li>Anyone with this phrase can access your funds</li>
                <li>This phrase will only be shown once</li>
            </ul>
        `;
        document.getElementById('wallet-info').appendChild(warningDiv);

        // Clear password fields
        document.getElementById('password').value = '';
        document.getElementById('confirm-password').value = '';

        // Reset login attempts on success
        loginAttempts = 0;

    } catch (error) {
        console.error('Error creating wallet:', error);
        loginAttempts++;
        
        // Show error with specific message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'mt-4 p-4 bg-red-100 text-red-700 rounded-md';
        errorDiv.textContent = error.message;
        document.getElementById('wallet-form').appendChild(errorDiv);
        
        // Remove error message after 5 seconds
        setTimeout(() => errorDiv.remove(), 5000);
    }
}

// Copy wallet address to clipboard with visual feedback
function copyToClipboard(text, element) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = element.textContent;
        element.textContent = 'Copied!';
        setTimeout(() => element.textContent = originalText, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Password strength real-time feedback
    const passwordInput = document.getElementById('password');
    const strengthIndicator = document.createElement('div');
    strengthIndicator.className = 'mt-1 text-sm';
    passwordInput.parentNode.appendChild(strengthIndicator);

    passwordInput.addEventListener('input', function() {
        const strength = checkPasswordStrength(this.value);
        strengthIndicator.innerHTML = strength.message.map(msg => 
            `<div class="text-${strength.isStrong ? 'green' : 'red'}-600">• ${msg}</div>`
        ).join('');
    });

    // Copy address functionality
    const walletAddress = document.getElementById('wallet-address');
    if (walletAddress) {
        walletAddress.addEventListener('click', function() {
            copyToClipboard(this.value, this);
        });
    }
});
