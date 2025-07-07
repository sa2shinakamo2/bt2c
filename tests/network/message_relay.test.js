/**
 * BT2C Message Relay Tests
 * 
 * This file contains unit tests for the message relay module.
 */

const { MessageRelay, RelayMode } = require('../../src/network/message_relay');
const EventEmitter = require('events');

// Mock NetworkManager
class MockNetworkManager extends EventEmitter {
  constructor() {
    super();
    this.peers = new Map();
    this.sentMessages = [];
    this.broadcastMessages = [];
  }
  
  getPeer(peerId) {
    return this.peers.get(peerId);
  }
  
  getPeers() {
    return Array.from(this.peers.values());
  }
  
  sendMessage(peerId, message) {
    this.sentMessages.push({ peerId, message });
    return true;
  }
  
  broadcastMessage(message) {
    this.broadcastMessages.push(message);
    return true;
  }
  
  addPeer(peer) {
    this.peers.set(peer.id, peer);
    this.emit('peer:connected', peer);
    return peer;
  }
  
  removePeer(peerId) {
    const peer = this.peers.get(peerId);
    if (peer) {
      this.peers.delete(peerId);
      this.emit('peer:disconnected', peer);
    }
    return peer;
  }
}

describe('MessageRelay', () => {
  let messageRelay;
  let networkManager;
  
  beforeEach(() => {
    // Create mock network manager
    networkManager = new MockNetworkManager();
    
    // Create message relay instance
    messageRelay = new MessageRelay({
      networkManager,
      maxRelayHops: 3,
      relayMode: RelayMode.SELECTIVE
    });
    
    // Add some test peers
    networkManager.addPeer({
      id: 'peer1',
      metadata: { isValidator: true },
      reputation: 80
    });
    
    networkManager.addPeer({
      id: 'peer2',
      metadata: { isValidator: false },
      reputation: 60
    });
    
    networkManager.addPeer({
      id: 'peer3',
      metadata: { isValidator: false },
      reputation: 40
    });
  });
  
  afterEach(() => {
    // Clean up
    messageRelay.close();
  });
  
  test('should initialize with default options', () => {
    const defaultRelay = new MessageRelay({ networkManager });
    expect(defaultRelay.options.maxRelayHops).toBeDefined();
    expect(defaultRelay.options.relayMode).toBe(RelayMode.SELECTIVE);
    expect(defaultRelay.options.relayThreshold).toBeDefined();
  });
  
  test('should process incoming message with no relay header', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' }
    };
    
    const processedMessage = messageRelay.processIncomingMessage('peer1', message);
    
    // Should add relay header
    expect(processedMessage.relay).toBeDefined();
    expect(processedMessage.relay.hops).toBe(0);
    expect(processedMessage.relay.origin).toBe('peer1');
    expect(processedMessage.relay.path).toEqual(['peer1']);
    
    // Original message should be preserved
    expect(processedMessage.type).toBe(message.type);
    expect(processedMessage.data).toEqual(message.data);
  });
  
  test('should process incoming message with existing relay header', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' },
      relay: {
        hops: 1,
        origin: 'originPeer',
        path: ['originPeer', 'peer1']
      }
    };
    
    const processedMessage = messageRelay.processIncomingMessage('peer2', message);
    
    // Should update relay header
    expect(processedMessage.relay.hops).toBe(2);
    expect(processedMessage.relay.origin).toBe('originPeer');
    expect(processedMessage.relay.path).toEqual(['originPeer', 'peer1', 'peer2']);
  });
  
  test('should not relay message that exceeds max hops', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' },
      relay: {
        hops: 3, // Already at max hops
        origin: 'originPeer',
        path: ['originPeer', 'peer1', 'peer2']
      }
    };
    
    const shouldRelay = messageRelay.shouldRelayMessage('peer3', message);
    expect(shouldRelay).toBe(false);
  });
  
  test('should not relay message that has already been through the peer', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' },
      relay: {
        hops: 2,
        origin: 'originPeer',
        path: ['originPeer', 'peer1', 'peer2']
      }
    };
    
    const shouldRelay = messageRelay.shouldRelayMessage('peer1', message);
    expect(shouldRelay).toBe(false);
  });
  
  test('should relay message in FLOOD mode', () => {
    // Set relay mode to FLOOD
    messageRelay.options.relayMode = RelayMode.FLOOD;
    
    const message = {
      type: 'test',
      data: { value: 'test data' },
      relay: {
        hops: 1,
        origin: 'originPeer',
        path: ['originPeer', 'peer1']
      }
    };
    
    // Should relay to all peers except those in path
    messageRelay.relayMessage('peer1', message);
    
    // Should have sent to peer2 and peer3
    expect(networkManager.sentMessages.length).toBe(2);
    
    const sentToPeer2 = networkManager.sentMessages.some(m => m.peerId === 'peer2');
    const sentToPeer3 = networkManager.sentMessages.some(m => m.peerId === 'peer3');
    
    expect(sentToPeer2).toBe(true);
    expect(sentToPeer3).toBe(true);
  });
  
  test('should relay message in SELECTIVE mode only to high reputation peers', () => {
    // Set relay mode to SELECTIVE with high threshold
    messageRelay.options.relayMode = RelayMode.SELECTIVE;
    messageRelay.options.relayThreshold = 50;
    
    const message = {
      type: 'test',
      data: { value: 'test data' },
      relay: {
        hops: 1,
        origin: 'originPeer',
        path: ['originPeer', 'peer1']
      }
    };
    
    // Should relay only to peer2 (reputation 60)
    messageRelay.relayMessage('peer1', message);
    
    // Should have sent to peer2 only
    expect(networkManager.sentMessages.length).toBe(1);
    expect(networkManager.sentMessages[0].peerId).toBe('peer2');
  });
  
  test('should relay message in VALIDATOR_ONLY mode only to validators', () => {
    // Set relay mode to VALIDATOR_ONLY
    messageRelay.options.relayMode = RelayMode.VALIDATOR_ONLY;
    
    const message = {
      type: 'test',
      data: { value: 'test data' },
      relay: {
        hops: 1,
        origin: 'originPeer',
        path: ['originPeer', 'peer2']
      }
    };
    
    // Should relay only to peer1 (validator)
    messageRelay.relayMessage('peer2', message);
    
    // Should have sent to peer1 only
    expect(networkManager.sentMessages.length).toBe(1);
    expect(networkManager.sentMessages[0].peerId).toBe('peer1');
  });
  
  test('should handle message with relay instructions', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' },
      relay: {
        hops: 1,
        origin: 'originPeer',
        path: ['originPeer', 'peer1'],
        instructions: {
          targetPeers: ['peer2']
        }
      }
    };
    
    // Should relay only to peer2 as specified in instructions
    messageRelay.relayMessage('peer1', message);
    
    // Should have sent to peer2 only
    expect(networkManager.sentMessages.length).toBe(1);
    expect(networkManager.sentMessages[0].peerId).toBe('peer2');
  });
  
  test('should create relay message with instructions', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' }
    };
    
    const relayMessage = messageRelay.createRelayMessage(message, {
      targetPeers: ['peer1', 'peer2'],
      maxHops: 2
    });
    
    expect(relayMessage.relay).toBeDefined();
    expect(relayMessage.relay.instructions).toBeDefined();
    expect(relayMessage.relay.instructions.targetPeers).toEqual(['peer1', 'peer2']);
    expect(relayMessage.relay.instructions.maxHops).toBe(2);
  });
  
  test('should send direct relay message to specific peer', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' }
    };
    
    messageRelay.sendDirectRelayMessage('peer2', message);
    
    // Should have sent to peer2
    expect(networkManager.sentMessages.length).toBe(1);
    expect(networkManager.sentMessages[0].peerId).toBe('peer2');
    
    // Message should have relay header
    const sentMessage = networkManager.sentMessages[0].message;
    expect(sentMessage.relay).toBeDefined();
    expect(sentMessage.relay.direct).toBe(true);
  });
  
  test('should broadcast relay message to network', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' }
    };
    
    messageRelay.broadcastRelayMessage(message);
    
    // Should have broadcast message
    expect(networkManager.broadcastMessages.length).toBe(1);
    
    // Message should have relay header
    const broadcastMessage = networkManager.broadcastMessages[0];
    expect(broadcastMessage.relay).toBeDefined();
    expect(broadcastMessage.relay.broadcast).toBe(true);
  });
  
  test('should handle peer disconnection', () => {
    // Set up spy on cleanup method
    const cleanupSpy = jest.spyOn(messageRelay, 'cleanupPeerRelays');
    
    // Simulate peer disconnection
    networkManager.removePeer('peer2');
    
    // Should have called cleanup
    expect(cleanupSpy).toHaveBeenCalledWith('peer2');
  });
  
  test('should track message IDs to prevent duplicates', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' },
      id: 'message-123'
    };
    
    // Process message first time
    const isDuplicate1 = messageRelay.isDuplicateMessage(message);
    expect(isDuplicate1).toBe(false);
    
    // Process same message again
    const isDuplicate2 = messageRelay.isDuplicateMessage(message);
    expect(isDuplicate2).toBe(true);
  });
  
  test('should expire old message IDs', () => {
    const message = {
      type: 'test',
      data: { value: 'test data' },
      id: 'message-456'
    };
    
    // Process message
    messageRelay.isDuplicateMessage(message);
    
    // Mock Date.now to simulate time passing
    const originalDateNow = Date.now;
    const currentTime = Date.now();
    
    try {
      // Fast forward beyond expiration time
      global.Date.now = jest.fn(() => currentTime + 3600000);
      
      // Clean up expired messages
      messageRelay.cleanupExpiredMessages();
      
      // Message should no longer be considered duplicate
      const isDuplicate = messageRelay.isDuplicateMessage(message);
      expect(isDuplicate).toBe(false);
    } finally {
      // Restore original Date.now
      global.Date.now = originalDateNow;
    }
  });
  
  test('should close and clean up resources', () => {
    // Set up spy on network manager removeListener
    const removeListenerSpy = jest.spyOn(networkManager, 'removeListener');
    
    // Close message relay
    messageRelay.close();
    
    // Should have removed event listeners
    expect(removeListenerSpy).toHaveBeenCalled();
    
    // Should have cleared interval
    expect(messageRelay.cleanupInterval).toBeNull();
  });
});
