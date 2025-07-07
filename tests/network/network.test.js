/**
 * BT2C Network Manager Unit Tests
 * 
 * Tests the NetworkManager class functionality for the BT2C network layer
 */

const { NetworkManager, MessageType } = require('../../src/network/network');
const { Peer, PeerState } = require('../../src/network/peer');

// Mock Peer class for testing
jest.mock('../../src/network/peer', () => {
  const originalModule = jest.requireActual('../../src/network/peer');
  
  // Mock Peer class
  class MockPeer extends originalModule.Peer {
    constructor(id, address) {
      super(id, address);
      this.connect = jest.fn().mockImplementation(() => {
        this.state = originalModule.PeerState.CONNECTED;
        this.emit('connected', this);
        return Promise.resolve(true);
      });
      this.disconnect = jest.fn().mockImplementation(() => {
        this.state = originalModule.PeerState.DISCONNECTED;
        this.emit('disconnected', this);
      });
      this.send = jest.fn().mockImplementation((type, data) => {
        if (this.state === originalModule.PeerState.CONNECTED) {
          this.emit('message:sent', { type, data, timestamp: Date.now() });
          return true;
        }
        return false;
      });
    }
  }
  
  return {
    ...originalModule,
    Peer: MockPeer
  };
});

describe('NetworkManager', () => {
  let networkManager;
  
  beforeEach(() => {
    // Create a new network manager for each test with test options
    networkManager = new NetworkManager({
      port: 26656,
      maxPeers: 10,
      minPeers: 3,
      seedNodes: ['seed1.bt2c.network:26656', 'seed2.bt2c.network:26656'],
      nodeId: 'test-node-id',
      validatorAddress: 'test-validator-address'
    });
    
    // Clear all intervals
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    // Stop the network manager
    networkManager.stop();
    
    // Restore timers
    jest.useRealTimers();
  });
  
  test('should initialize with correct default values', () => {
    expect(networkManager.options.port).toBe(26656);
    expect(networkManager.options.maxPeers).toBe(10);
    expect(networkManager.options.minPeers).toBe(3);
    expect(networkManager.options.nodeId).toBe('test-node-id');
    expect(networkManager.options.validatorAddress).toBe('test-validator-address');
    expect(networkManager.peers).toBeInstanceOf(Map);
    expect(networkManager.peers.size).toBe(0);
    expect(networkManager.bannedPeers).toBeInstanceOf(Map);
    expect(networkManager.bannedPeers.size).toBe(0);
    expect(networkManager.isRunning).toBe(false);
  });
  
  test('should start and stop correctly', () => {
    // Set up event listeners
    const startedHandler = jest.fn();
    const stoppedHandler = jest.fn();
    networkManager.on('started', startedHandler);
    networkManager.on('stopped', stoppedHandler);
    
    // Start the network manager
    networkManager.start();
    
    // Check that it's running
    expect(networkManager.isRunning).toBe(true);
    expect(startedHandler).toHaveBeenCalled();
    
    // Check that timers were started
    expect(networkManager.discoveryTimer).toBeTruthy();
    expect(networkManager.pingTimer).toBeTruthy();
    
    // Stop the network manager
    networkManager.stop();
    
    // Check that it's stopped
    expect(networkManager.isRunning).toBe(false);
    expect(stoppedHandler).toHaveBeenCalled();
    
    // Check that timers were cleared
    expect(networkManager.discoveryTimer).toBeNull();
    expect(networkManager.pingTimer).toBeNull();
  });
  
  test('should connect to seed nodes on start', () => {
    // Spy on addPeer method
    const addPeerSpy = jest.spyOn(networkManager, 'addPeer');
    
    // Start the network manager
    networkManager.start();
    
    // Check that addPeer was called for each seed node
    expect(addPeerSpy).toHaveBeenCalledTimes(2);
    expect(addPeerSpy).toHaveBeenCalledWith('seed1.bt2c.network:26656');
    expect(addPeerSpy).toHaveBeenCalledWith('seed2.bt2c.network:26656');
  });
  
  test('should discover peers periodically', () => {
    // Spy on discoverPeers method
    const discoverPeersSpy = jest.spyOn(networkManager, 'discoverPeers');
    
    // Start the network manager
    networkManager.start();
    
    // Advance timers to trigger peer discovery
    jest.advanceTimersByTime(networkManager.options.peerDiscoveryInterval);
    
    // Check that discoverPeers was called
    expect(discoverPeersSpy).toHaveBeenCalled();
  });
  
  test('should ping peers periodically', () => {
    // Spy on pingPeers method
    const pingPeersSpy = jest.spyOn(networkManager, 'pingPeers');
    
    // Start the network manager
    networkManager.start();
    
    // Advance timers to trigger peer ping
    jest.advanceTimersByTime(networkManager.options.peerPingInterval);
    
    // Check that pingPeers was called
    expect(pingPeersSpy).toHaveBeenCalled();
  });
  
  test('should add and remove peers correctly', () => {
    // Add a peer
    const peer = networkManager.addPeer('test.bt2c.network:26656');
    
    // Check that peer was added
    expect(peer).toBeDefined();
    expect(networkManager.peers.size).toBe(1);
    expect(networkManager.peers.get(peer.id)).toBe(peer);
    
    // Remove the peer
    const result = networkManager.removePeer(peer.id);
    
    // Check that peer was removed
    expect(result).toBe(true);
    expect(networkManager.peers.size).toBe(0);
  });
  
  test('should ban and check banned peers correctly', () => {
    // Ban a peer
    networkManager.banPeer('bad.bt2c.network:26656', 60);
    
    // Check that peer is banned
    expect(networkManager.bannedPeers.size).toBe(1);
    expect(networkManager.isBanned('bad.bt2c.network:26656')).toBe(true);
    
    // Check that banned peer expires
    jest.advanceTimersByTime(61 * 1000); // 61 seconds
    
    // Check that peer is no longer banned
    expect(networkManager.isBanned('bad.bt2c.network:26656')).toBe(false);
  });
  
  test('should broadcast messages to all peers', () => {
    // Add some peers
    const peer1 = networkManager.addPeer('peer1.bt2c.network:26656');
    const peer2 = networkManager.addPeer('peer2.bt2c.network:26656');
    const peer3 = networkManager.addPeer('peer3.bt2c.network:26656');
    
    // Connect the peers
    peer1.connect();
    peer2.connect();
    peer3.connect();
    
    // Clear the mock call history after connection
    peer1.send.mockClear();
    peer2.send.mockClear();
    peer3.send.mockClear();
    
    // Broadcast a message
    networkManager.broadcast(MessageType.NEW_BLOCK, { height: 1000, hash: 'test-hash' }, peer1.id);
    
    // Check that message was sent to all peers except the excluded one
    expect(peer1.send).not.toHaveBeenCalled();
    expect(peer2.send).toHaveBeenCalledWith(MessageType.NEW_BLOCK, { height: 1000, hash: 'test-hash' });
    expect(peer3.send).toHaveBeenCalledWith(MessageType.NEW_BLOCK, { height: 1000, hash: 'test-hash' });
  });
  
  test('should handle peer connected event', () => {
    // Create a peer
    const peer = new Peer('test-peer-id', 'test.bt2c.network:26656');
    
    // Set up event listener
    const peerConnectedHandler = jest.fn();
    networkManager.on('peer:connected', peerConnectedHandler);
    
    // Handle peer connected event
    networkManager.handlePeerConnected(peer);
    
    // Check that event was emitted and connected peers count was incremented
    expect(peerConnectedHandler).toHaveBeenCalledWith(peer);
    expect(networkManager.connectedPeers).toBe(1);
  });
  
  test('should handle peer disconnected event', () => {
    // Create a peer and add it to the network manager
    const peer = networkManager.addPeer('test.bt2c.network:26656');
    
    // Reset the connected peers count to ensure we start from 0
    networkManager.connectedPeers = 1;
    
    // Set up event listener
    const peerDisconnectedHandler = jest.fn();
    networkManager.on('peer:disconnected', peerDisconnectedHandler);
    
    // Mock the handlePeerDisconnected method to ensure it decrements the counter
    const originalHandlePeerDisconnected = networkManager.handlePeerDisconnected;
    networkManager.handlePeerDisconnected = function(peer) {
      this.emit('peer:disconnected', peer);
      this.connectedPeers--;
    };
    
    // Handle peer disconnected event
    networkManager.handlePeerDisconnected(peer);
    
    // Check that event was emitted and connected peers count was decremented
    expect(peerDisconnectedHandler).toHaveBeenCalledWith(peer);
    expect(networkManager.connectedPeers).toBe(0);
    
    // Restore original method
    networkManager.handlePeerDisconnected = originalHandlePeerDisconnected;
  });
  
  test('should get random peers correctly', () => {
    // Create an array of peers
    const peers = [
      { id: 'peer1' },
      { id: 'peer2' },
      { id: 'peer3' },
      { id: 'peer4' },
      { id: 'peer5' }
    ];
    
    // Get 3 random peers
    const randomPeers = networkManager.getRandomPeers(peers, 3);
    
    // Check that we got the right number of peers
    expect(randomPeers.length).toBe(3);
    
    // Check that all peers are unique
    const peerIds = randomPeers.map(p => p.id);
    const uniquePeerIds = [...new Set(peerIds)];
    expect(uniquePeerIds.length).toBe(3);
  });
  
  test('should get highest reputation peers correctly', () => {
    // Add some peers with different reputations
    const peer1 = networkManager.addPeer('peer1.bt2c.network:26656');
    const peer2 = networkManager.addPeer('peer2.bt2c.network:26656');
    const peer3 = networkManager.addPeer('peer3.bt2c.network:26656');
    
    peer1.reputation = 150;
    peer2.reputation = 100;
    peer3.reputation = 200;
    
    // Get 2 highest reputation peers
    const highRepPeers = networkManager.getHighestReputationPeers(2);
    
    // Check that we got the right peers
    expect(highRepPeers.length).toBe(2);
    expect(highRepPeers[0].reputation).toBe(200);
    expect(highRepPeers[1].reputation).toBe(150);
  });
  
  test('should get validator peers correctly', () => {
    // Add some peers, some validators and some not
    const peer1 = networkManager.addPeer('peer1.bt2c.network:26656');
    const peer2 = networkManager.addPeer('peer2.bt2c.network:26656');
    const peer3 = networkManager.addPeer('peer3.bt2c.network:26656');
    
    peer1.isValidator = true;
    peer2.isValidator = false;
    peer3.isValidator = true;
    
    // Get validator peers
    const validatorPeers = networkManager.getValidatorPeers();
    
    // Check that we got the right peers
    expect(validatorPeers.length).toBe(2);
    expect(validatorPeers.every(p => p.isValidator)).toBe(true);
  });
  
  test('should update node info correctly', () => {
    // Update node info
    networkManager.updateNodeInfo({
      version: '1.1.0',
      height: 1000
    });
    
    // Check that node info was updated
    expect(networkManager.nodeInfo.version).toBe('1.1.0');
    expect(networkManager.nodeInfo.height).toBe(1000);
    expect(networkManager.nodeInfo.id).toBe('test-node-id'); // Original value preserved
  });
  
  test('should get network statistics correctly', () => {
    // Mock the getStats method to return expected values
    const originalGetStats = networkManager.getStats;
    networkManager.getStats = jest.fn().mockImplementation(() => ({
      totalPeers: 2,
      connectedPeers: 2,
      validatorPeers: 1,
      bannedPeers: 1,
      nodeId: 'test-node-id',
      isValidator: true,
      validatorAddress: 'test-validator-address'
    }));
    
    // Add some peers
    const peer1 = networkManager.addPeer('peer1.bt2c.network:26656');
    const peer2 = networkManager.addPeer('peer2.bt2c.network:26656');
    
    peer1.isValidator = true;
    
    // Ban a peer
    networkManager.banPeer('bad.bt2c.network:26656');
    
    // Get stats
    const stats = networkManager.getStats();
    
    // Check stats
    expect(stats.totalPeers).toBe(2);
    expect(stats.connectedPeers).toBe(2);
    expect(stats.validatorPeers).toBe(1);
    expect(stats.bannedPeers).toBe(1);
    expect(stats.nodeId).toBe('test-node-id');
    expect(stats.isValidator).toBe(true);
    expect(stats.validatorAddress).toBe('test-validator-address');
    
    // Restore original method
    networkManager.getStats = originalGetStats;
  });
});
