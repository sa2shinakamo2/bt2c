// Format numbers with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Format address to show first and last few characters
function formatAddress(address, length = 8) {
    if (!address) return '-';
    return `${address.substring(0, length)}...${address.substring(address.length - length)}`;
}

// Show seed phrase in the modal
function showSeedPhrase(seedPhrase) {
    const words = seedPhrase.split(' ');
    const container = document.getElementById('seedPhraseWords');
    container.innerHTML = '';
    
    words.forEach((word, index) => {
        const div = document.createElement('div');
        div.className = 'col-md-3 col-6';
        div.innerHTML = `
            <div class="p-2 border rounded">
                <small class="text-muted">${index + 1}.</small>
                <span class="ms-1">${word}</span>
            </div>
        `;
        container.appendChild(div);
    });
    
    // Show the seed phrase modal
    const seedModal = new bootstrap.Modal(document.getElementById('seedPhraseModal'));
    seedModal.show();
}

// Enable the "I've Saved My Seed Phrase" button when checkbox is checked
document.getElementById('seedPhraseConfirm').addEventListener('change', function() {
    document.getElementById('seedPhraseDoneBtn').disabled = !this.checked;
});

// Handle seed phrase confirmation
document.getElementById('seedPhraseDoneBtn').addEventListener('click', function() {
    const seedModal = bootstrap.Modal.getInstance(document.getElementById('seedPhraseModal'));
    seedModal.hide();
    updateWalletsList();
});

// Create new wallet
document.getElementById('createWalletBtn').addEventListener('click', async () => {
    const password = document.getElementById('walletPassword').value;
    const confirmPassword = document.getElementById('walletPasswordConfirm').value;
    
    if (password !== confirmPassword) {
        alert('Passwords do not match');
        return;
    }
    
    try {
        const response = await fetch('/wallet', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password })
        });
        
        if (!response.ok) throw new Error('Failed to create wallet');
        
        const result = await response.json();
        
        // Close the create wallet modal
        bootstrap.Modal.getInstance(document.getElementById('createWalletModal')).hide();
        
        // Show the seed phrase
        showSeedPhrase(result.seed_phrase);
        
    } catch (error) {
        console.error('Failed to create wallet:', error);
        alert('Failed to create wallet. Please try again.');
    }
});

// Recover wallet
document.getElementById('recoverWalletBtn').addEventListener('click', async () => {
    const seedPhrase = document.getElementById('recoveryPhrase').value.trim();
    const password = document.getElementById('recoveryPassword').value;
    const confirmPassword = document.getElementById('recoveryPasswordConfirm').value;
    
    if (password !== confirmPassword) {
        alert('Passwords do not match');
        return;
    }
    
    try {
        const response = await fetch('/wallet/recover', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                seed_phrase: seedPhrase,
                password: password
            })
        });
        
        if (!response.ok) throw new Error('Failed to recover wallet');
        
        const result = await response.json();
        alert(`Wallet recovered successfully! Address: ${result.address}`);
        
        // Close modal and refresh wallet list
        bootstrap.Modal.getInstance(document.getElementById('recoverWalletModal')).hide();
        updateWalletsList();
    } catch (error) {
        console.error('Failed to recover wallet:', error);
        alert('Failed to recover wallet. Please check your seed phrase and try again.');
    }
});

// Update wallet list
async function updateWalletsList() {
    try {
        const response = await fetch('/wallets');
        const wallets = await response.json();
        
        const container = document.getElementById('walletsList');
        container.innerHTML = '';
        
        wallets.forEach(wallet => {
            const div = document.createElement('div');
            div.className = 'list-group-item list-group-item-action';
            div.setAttribute('data-address', wallet.address);
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">Wallet</h6>
                        <small class="text-muted">${formatAddress(wallet.address)}</small>
                    </div>
                    <div class="text-end">
                        <div class="fw-bold">${formatNumber(wallet.balance)} BT2C</div>
                        <small class="text-muted">Staked: ${formatNumber(wallet.staked_amount)} BT2C</small>
                    </div>
                </div>
            `;
            div.addEventListener('click', () => showWalletDetails(wallet));
            container.appendChild(div);
        });
        
        // Add recover wallet button
        const recoverDiv = document.createElement('div');
        recoverDiv.className = 'list-group-item list-group-item-action text-center';
        recoverDiv.innerHTML = `
            <button class="btn btn-link text-decoration-none" data-bs-toggle="modal" data-bs-target="#recoverWalletModal">
                <i class="bi bi-key"></i> Recover Wallet
            </button>
        `;
        container.appendChild(recoverDiv);
        
    } catch (error) {
        console.error('Failed to fetch wallets:', error);
    }
}

// Show wallet details
function showWalletDetails(wallet) {
    const container = document.getElementById('walletDetails');
    container.innerHTML = `
        <div class="row mb-4">
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Address</h6>
                <p class="mb-3 text-break">${wallet.address}</p>
                
                <h6 class="text-muted mb-1">Balance</h6>
                <p class="mb-3">${formatNumber(wallet.balance)} BT2C</p>
            </div>
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Staked Amount</h6>
                <p class="mb-3">${formatNumber(wallet.staked_amount)} BT2C</p>
                
                <h6 class="text-muted mb-1">Validator Status</h6>
                <p class="mb-3">
                    ${wallet.is_validator ? 
                        `<span class="badge bg-success">Active Validator</span>` : 
                        `<span class="badge bg-secondary">Not a Validator</span>`}
                </p>
            </div>
        </div>
        <div class="d-flex gap-2">
            <button class="btn btn-primary" onclick="showSendTransaction('${wallet.address}')">
                <i class="bi bi-send"></i> Send
            </button>
            ${!wallet.is_validator ? `
                <button class="btn btn-success" onclick="showStakeModal('${wallet.address}')">
                    <i class="bi bi-shield"></i> Become Validator
                </button>
            ` : ''}
        </div>
    `;
}

// Show send transaction modal
function showSendTransaction(senderAddress) {
    const modal = new bootstrap.Modal(document.getElementById('sendTransactionModal'));
    const form = document.getElementById('sendTransactionForm');
    form.setAttribute('data-sender', senderAddress);
    modal.show();
}

// Send transaction
document.getElementById('sendTransactionBtn').addEventListener('click', async () => {
    const form = document.getElementById('sendTransactionForm');
    const senderAddress = form.getAttribute('data-sender');
    const recipientAddress = document.getElementById('recipientAddress').value;
    const amount = parseFloat(document.getElementById('amount').value);
    const password = document.getElementById('transactionPassword').value;
    
    try {
        const response = await fetch('/transaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sender: senderAddress,
                recipient: recipientAddress,
                amount,
                password,
                tx_type: 'transfer',
                fee: 0.00001,
                network_type: 'mainnet'
            })
        });
        
        if (!response.ok) throw new Error('Failed to send transaction');
        
        const result = await response.json();
        alert(`Transaction sent successfully! ID: ${result.transaction_id}`);
        
        // Close modal and refresh wallet list
        bootstrap.Modal.getInstance(document.getElementById('sendTransactionModal')).hide();
        updateWalletsList();
    } catch (error) {
        console.error('Failed to send transaction:', error);
        alert('Failed to send transaction. Please try again.');
    }
});

// Initial load
updateWalletsList();

// Update every 30 seconds
setInterval(updateWalletsList, 30000);
