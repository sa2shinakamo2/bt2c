// Utility functions
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function truncateHash(hash) {
    return `${hash.substring(0, 6)}...${hash.substring(hash.length - 4)}`;
}

// Search functionality
let searchTimeout;

function debounceSearch(query) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => performSearch(query), 300);
}

async function performSearch(query) {
    if (!query.trim()) {
        document.getElementById('searchResults').classList.add('hidden');
        return;
    }

    try {
        const response = await fetch(`/api/v1/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Search failed');
        const results = await response.json();
        displaySearchResults(results);
    } catch (error) {
        console.error('Search error:', error);
        showError('Failed to perform search. Please try again.');
    }
}

function displaySearchResults(results) {
    const resultsDiv = document.getElementById('searchResults');
    const resultsContent = document.getElementById('resultsContent');
    resultsContent.innerHTML = '';

    if (!results.data || results.data.length === 0) {
        resultsContent.innerHTML = `
            <div class="bg-yellow-50 p-4 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-yellow-800">No results found</h3>
                        <div class="mt-2 text-sm text-yellow-700">
                            <p>Try searching for:</p>
                            <ul class="list-disc pl-5 mt-1">
                                <li>Block height (e.g., "1000")</li>
                                <li>Transaction hash (e.g., "0x...")</li>
                                <li>Address (e.g., "0x...")</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>`;
    } else {
        results.data.forEach(item => {
            let itemHtml = '';
            if ('height' in item) { // Block
                itemHtml = `
                    <div class="border rounded-lg p-4 hover:bg-gray-50">
                        <div class="flex justify-between items-center">
                            <div>
                                <h4 class="text-sm font-medium text-gray-900">Block #${item.height}</h4>
                                <p class="text-sm text-gray-500">Hash: ${truncateHash(item.hash)}</p>
                                <p class="text-sm text-gray-500">Validator: ${item.validator}</p>
                            </div>
                            <div class="text-sm text-gray-500">
                                ${item.transactions} transactions<br>
                                ${formatTimestamp(item.timestamp)}
                            </div>
                        </div>
                    </div>`;
            } else { // Transaction
                itemHtml = `
                    <div class="border rounded-lg p-4 hover:bg-gray-50">
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span class="text-sm font-medium text-gray-900">Tx: ${truncateHash(item.hash)}</span>
                                <span class="text-sm ${item.status === 'confirmed' ? 'text-green-600' : 'text-yellow-600'}">
                                    ${item.status}
                                </span>
                            </div>
                            <div class="text-sm text-gray-500">
                                From: ${truncateHash(item.from)}<br>
                                To: ${truncateHash(item.to)}
                            </div>
                            <div class="flex justify-between text-sm">
                                <span class="text-gray-500">${item.amount} BT2C</span>
                                <span class="text-gray-500">${formatTimestamp(item.timestamp)}</span>
                            </div>
                        </div>
                    </div>`;
            }
            resultsContent.innerHTML += itemHtml;
        });
    }
    resultsDiv.classList.remove('hidden');
}

function showError(message) {
    const resultsDiv = document.getElementById('searchResults');
    const resultsContent = document.getElementById('resultsContent');
    resultsContent.innerHTML = `
        <div class="bg-red-50 p-4 rounded-md">
            <div class="flex">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">Error</h3>
                    <div class="mt-2 text-sm text-red-700">
                        <p>${message}</p>
                    </div>
                </div>
            </div>
        </div>`;
    resultsDiv.classList.remove('hidden');
}

// Load and display latest blocks
async function loadLatestBlocks() {
    try {
        const response = await fetch('/api/v1/blocks/latest');
        if (!response.ok) throw new Error('Failed to load blocks');
        const blocks = await response.json();
        const blocksDiv = document.getElementById('latestBlocks');
        blocksDiv.innerHTML = blocks.slice(0, 5).map(block => `
            <div class="border rounded-lg p-4 hover:bg-gray-50">
                <div class="flex justify-between items-center">
                    <div>
                        <h4 class="text-sm font-medium text-gray-900">Block #${block.height}</h4>
                        <p class="text-sm text-gray-500">Hash: ${truncateHash(block.hash)}</p>
                        <p class="text-sm text-gray-500">Validator: ${block.validator}</p>
                    </div>
                    <div class="text-sm text-gray-500 text-right">
                        ${block.transactions} transactions<br>
                        ${formatTimestamp(block.timestamp)}
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading blocks:', error);
        document.getElementById('latestBlocks').innerHTML = `
            <div class="bg-red-50 p-4 rounded-md">
                <p class="text-sm text-red-700">Failed to load latest blocks</p>
            </div>`;
    }
}

// Load and display latest transactions
async function loadLatestTransactions() {
    try {
        const response = await fetch('/api/v1/transactions/latest');
        if (!response.ok) throw new Error('Failed to load transactions');
        const transactions = await response.json();
        const txDiv = document.getElementById('latestTransactions');
        txDiv.innerHTML = transactions.slice(0, 5).map(tx => `
            <div class="border rounded-lg p-4 hover:bg-gray-50">
                <div class="space-y-2">
                    <div class="flex justify-between">
                        <span class="text-sm font-medium text-gray-900">Tx: ${truncateHash(tx.hash)}</span>
                        <span class="text-sm ${tx.status === 'confirmed' ? 'text-green-600' : 'text-yellow-600'}">
                            ${tx.status}
                        </span>
                    </div>
                    <div class="text-sm text-gray-500">
                        From: ${truncateHash(tx.from)}<br>
                        To: ${truncateHash(tx.to)}
                    </div>
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-500">${tx.amount} BT2C</span>
                        <span class="text-gray-500">${formatTimestamp(tx.timestamp)}</span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading transactions:', error);
        document.getElementById('latestTransactions').innerHTML = `
            <div class="bg-red-50 p-4 rounded-md">
                <p class="text-sm text-red-700">Failed to load latest transactions</p>
            </div>`;
    }
}

// Load and display network stats
async function loadNetworkStats() {
    try {
        const response = await fetch('/api/v1/stats');
        if (!response.ok) throw new Error('Failed to load network stats');
        const stats = await response.json();
        document.getElementById('networkStats').innerHTML = `
            <div class="px-4 py-5 bg-gray-50 shadow rounded-lg overflow-hidden sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Total Blocks</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">${stats.totalBlocks}</dd>
            </div>
            <div class="px-4 py-5 bg-gray-50 shadow rounded-lg overflow-hidden sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Active Validators</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">${stats.activeValidators}</dd>
            </div>
            <div class="px-4 py-5 bg-gray-50 shadow rounded-lg overflow-hidden sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Total Transactions</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">${stats.totalTransactions}</dd>
            </div>
        `;
    } catch (error) {
        console.error('Error loading network stats:', error);
        document.getElementById('networkStats').innerHTML = `
            <div class="bg-red-50 p-4 rounded-md">
                <p class="text-sm text-red-700">Failed to load network statistics</p>
            </div>`;
    }
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Set up search input handler
    const searchInput = document.getElementById('search');
    searchInput.addEventListener('input', (e) => debounceSearch(e.target.value));
    
    // Set up search button handler
    const searchButton = document.getElementById('searchButton');
    searchButton.addEventListener('click', () => performSearch(searchInput.value));

    // Load initial data
    loadLatestBlocks();
    loadLatestTransactions();
    loadNetworkStats();

    // Refresh data periodically
    setInterval(loadLatestBlocks, 30000); // Every 30 seconds
    setInterval(loadLatestTransactions, 30000);
    setInterval(loadNetworkStats, 60000); // Every minute
});
