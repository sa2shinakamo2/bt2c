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
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
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

    if (!results || !results.data || results.data.length === 0) {
        resultsContent.innerHTML = `
            <div class="bg-yellow-50 p-4 rounded-md">
                <div class="flex">
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-yellow-800">No results found</h3>
                    </div>
                </div>
            </div>`;
        resultsDiv.classList.remove('hidden');
        return;
    }

    // Display results
    resultsDiv.classList.remove('hidden');
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'fixed bottom-4 right-4 bg-red-50 p-4 rounded-md shadow-lg';
    errorDiv.innerHTML = `
        <div class="flex">
            <div class="ml-3">
                <p class="text-sm font-medium text-red-800">${message}</p>
            </div>
        </div>
    `;
    document.body.appendChild(errorDiv);
    setTimeout(() => errorDiv.remove(), 5000);
}

// Load and display latest blocks
async function loadLatestBlocks() {
    try {
        console.log('Loading blocks...');
        const response = await fetch('/api/blocks');
        if (!response.ok) throw new Error('Failed to load blocks');
        const data = await response.json();
        console.log('Blocks data:', data);
        
        const blocksDiv = document.getElementById('latestBlocks');
        if (!blocksDiv) {
            console.error('Blocks container not found');
            return;
        }

        if (!data.blocks || !Array.isArray(data.blocks)) {
            throw new Error('Invalid blocks data format');
        }

        blocksDiv.innerHTML = data.blocks.slice(0, 5).map(block => `
            <div class="border rounded-lg p-4 hover:bg-gray-50">
                <div class="flex justify-between items-center">
                    <div>
                        <h4 class="text-sm font-medium text-gray-900">Block #${block.height}</h4>
                        <p class="text-sm text-gray-500">Hash: ${truncateHash(block.hash)}</p>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading blocks:', error);
        const blocksDiv = document.getElementById('latestBlocks');
        if (blocksDiv) {
            blocksDiv.innerHTML = `
                <div class="bg-red-50 p-4 rounded-md">
                    <p class="text-sm text-red-700">Failed to load latest blocks: ${error.message}</p>
                </div>`;
        }
    }
}

// Load and display network stats
async function loadNetworkStats() {
    try {
        console.log('Loading network stats...');
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error('Failed to load network stats');
        const stats = await response.json();
        console.log('Network stats:', stats);

        const statsDiv = document.getElementById('networkStats');
        if (!statsDiv) {
            console.error('Network stats container not found');
            return;
        }

        statsDiv.innerHTML = `
            <div class="bg-white shadow rounded-lg px-4 py-5 sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Network Status</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">${stats.status}</dd>
            </div>
            <div class="bg-white shadow rounded-lg px-4 py-5 sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Version</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">${stats.version}</dd>
            </div>
            <div class="bg-white shadow rounded-lg px-4 py-5 sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Network</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">${stats.network}</dd>
            </div>
        `;
    } catch (error) {
        console.error('Error loading network stats:', error);
        const statsDiv = document.getElementById('networkStats');
        if (statsDiv) {
            statsDiv.innerHTML = `
                <div class="bg-red-50 p-4 rounded-md">
                    <p class="text-sm text-red-700">Failed to load network statistics: ${error.message}</p>
                </div>`;
        }
    }
}

// Load and display validators
async function loadValidators() {
    try {
        console.log('Loading validators...');
        const response = await fetch('/api/validators');
        if (!response.ok) throw new Error('Failed to load validators');
        const data = await response.json();
        console.log('Validators data:', data);

        const validatorsDiv = document.getElementById('validators');
        if (!validatorsDiv) {
            console.error('Validators container not found');
            return;
        }

        if (!data.validators || !Array.isArray(data.validators)) {
            throw new Error('Invalid validators data format');
        }

        validatorsDiv.innerHTML = data.validators.map(validator => `
            <div class="border rounded-lg p-4 hover:bg-gray-50">
                <div class="flex justify-between items-center">
                    <div>
                        <h4 class="text-sm font-medium text-gray-900">Validator</h4>
                        <p class="text-sm text-gray-500">Address: ${truncateHash(validator.address)}</p>
                        <p class="text-sm text-gray-500">Stake: ${validator.stake} BT2C</p>
                        <p class="text-sm text-gray-500">Status: ${validator.status}</p>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading validators:', error);
        const validatorsDiv = document.getElementById('validators');
        if (validatorsDiv) {
            validatorsDiv.innerHTML = `
                <div class="bg-red-50 p-4 rounded-md">
                    <p class="text-sm text-red-700">Failed to load validators: ${error.message}</p>
                </div>`;
        }
    }
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Explorer page loaded');
    
    // Set up search input handler
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => debounceSearch(e.target.value));
    } else {
        console.error('Search input not found');
    }

    // Set up search button handler
    const searchButton = document.getElementById('searchButton');
    if (searchButton) {
        searchButton.addEventListener('click', () => {
            const searchInput = document.getElementById('search');
            if (searchInput) {
                performSearch(searchInput.value);
            }
        });
    } else {
        console.error('Search button not found');
    }

    // Load initial data
    loadLatestBlocks();
    loadNetworkStats();
    loadValidators();

    // Refresh data periodically
    setInterval(loadLatestBlocks, 30000); // Every 30 seconds
    setInterval(loadNetworkStats, 60000); // Every minute
    setInterval(loadValidators, 60000); // Every minute
});
