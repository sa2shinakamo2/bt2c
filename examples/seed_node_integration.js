/**
 * BT2C Network Integration Example
 * 
 * This example shows how to integrate the Bitcoin-style seed node system
 * with the existing BT2C NetworkManager.
 */

const { NetworkManager } = require('./network');
const { SeedNodeSystem } = require('./seed_node_system');
const os = require('os');
const path = require('path');

/**
 * Example of integrating the seed node system with NetworkManager
 */
async function main() {
  // Configuration
  const config = {
    // Network configuration
    port: 8334,
    maxPeers: 50,
    minPeers: 10,
    
    // Seed node configuration
    isSeedNode: true, // Set to true if this node should act as a seed node
    dataDir: path.join(os.homedir(), '.bt2c'),
    
    // DNS seeds (domain names that resolve to reliable seed nodes)
    dnsSeeds: [
      'seed1.bt2c.network',
      'seed2.bt2c.network',
      'seed3.bt2c.network'
    ],
    
    // Hardcoded seed nodes (fallback if DNS seeds are unavailable)
    hardcodedSeeds: [
      'bt2c.network:8334' // Your main validator/seed node
    ]
  };
  
  // Create network manager
  const networkManager = new NetworkManager({
    port: config.port,
    maxPeers: config.maxPeers,
    minPeers: config.minPeers
  });
  
  // Create seed node system
  const seedNodeSystem = new SeedNodeSystem({
    networkManager,
    dnsSeeds: config.dnsSeeds,
    hardcodedSeeds: config.hardcodedSeeds,
    isSeedNode: config.isSeedNode,
    defaultPort: config.port,
    dataDir: config.dataDir
  });
  
  // Start the network manager
  console.log('Starting network manager...');
  networkManager.start();
  
  // Start the seed node system
  console.log('Starting seed node system...');
  await seedNodeSystem.start();
  
  // Get bootstrap peers for initial connection
  console.log('Getting bootstrap peers...');
  const bootstrapPeers = await seedNodeSystem.getBootstrapPeers();
  console.log(`Found ${bootstrapPeers.length} bootstrap peers`);
  
  // Connect to bootstrap peers
  for (const peerAddress of bootstrapPeers) {
    networkManager.addPeer(peerAddress);
  }
  
  // Register network events to update peer storage
  
  // When a peer connects successfully
  networkManager.on('peer:connected', (peer) => {
    seedNodeSystem.addPeer(peer.address, { score: 1 });
  });
  
  // When a peer disconnects
  networkManager.on('peer:disconnected', (peer) => {
    // Don't remove the peer, just update its last seen time
    seedNodeSystem.addPeer(peer.address);
  });
  
  // When a peer is banned
  networkManager.on('peer:banned', (peer) => {
    seedNodeSystem.updatePeerScore(peer.address, -10);
  });
  
  // Save peers periodically (every 15 minutes)
  setInterval(() => {
    seedNodeSystem.savePeers();
  }, 15 * 60 * 1000);
  
  console.log('BT2C network with Bitcoin-style seed node system is running');
  
  // Handle shutdown
  process.on('SIGINT', async () => {
    console.log('Shutting down...');
    await seedNodeSystem.stop();
    networkManager.stop();
    process.exit(0);
  });
}

// Run the example
if (require.main === module) {
  main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
  });
}

module.exports = { main };
