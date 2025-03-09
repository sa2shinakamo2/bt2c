// Format numbers with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Format hash to show first and last few characters
function formatHash(hash, length = 8) {
    if (!hash) return '-';
    return `${hash.substring(0, length)}...${hash.substring(hash.length - length)}`;
}

// Update network statistics
function updateNetworkStats(data) {
    document.getElementById('chainHeight').textContent = formatNumber(data.chain_height);
    document.getElementById('totalSupply').textContent = formatNumber(data.total_supply) + ' BT2C';
    document.getElementById('totalStaked').textContent = formatNumber(data.total_staked) + ' BT2C';
    document.getElementById('activeValidators').textContent = data.validators.length;
}

// Update latest blocks table
function updateLatestBlocks(blocks) {
    const tbody = document.getElementById('latestBlocks');
    tbody.innerHTML = '';
    
    blocks.forEach(block => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatNumber(block.height)}</td>
            <td>${moment(block.timestamp * 1000).fromNow()}</td>
            <td>${block.num_transactions}</td>
            <td class="address-cell">${formatHash(block.validator)}</td>
            <td class="hash-cell">${formatHash(block.hash)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Update pending transactions
function updatePendingTransactions(transactions) {
    const container = document.getElementById('pendingTransactions');
    container.innerHTML = '';
    
    if (transactions.length === 0) {
        container.innerHTML = '<div class="list-group-item">No pending transactions</div>';
        return;
    }
    
    transactions.forEach(tx => {
        const div = document.createElement('div');
        div.className = 'list-group-item';
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <div class="hash-cell">${formatHash(tx.id)}</div>
                    <small class="text-muted">
                        From: ${formatHash(tx.sender)} To: ${formatHash(tx.recipient)}
                    </small>
                </div>
                <div class="text-end">
                    <div class="transaction-amount">${tx.amount} BT2C</div>
                    <small class="transaction-time">${tx.type}</small>
                </div>
            </div>
        `;
        container.appendChild(div);
    });
}

// Update validators table
function updateValidators(validators) {
    const tbody = document.getElementById('validatorsList');
    tbody.innerHTML = '';
    
    validators.forEach(validator => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="address-cell">${formatHash(validator.address)}</td>
            <td>${validator.power}</td>
            <td>${validator.total_blocks}</td>
            <td>
                <span class="badge bg-success validator-badge">Active</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Search functionality
document.querySelector('form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;
    
    try {
        // TODO: Implement search functionality
        console.log('Searching for:', query);
    } catch (error) {
        console.error('Search failed:', error);
    }
});

// Fetch and update data periodically
async function fetchData() {
    try {
        const response = await fetch('/explorer');
        const data = await response.json();
        
        updateNetworkStats(data);
        updateLatestBlocks(data.latest_blocks);
        updatePendingTransactions(data.pending_transactions);
        updateValidators(data.validators);
    } catch (error) {
        console.error('Failed to fetch explorer data:', error);
    }
}

// Initial load
fetchData();

// Update every 10 seconds
setInterval(fetchData, 10000);
