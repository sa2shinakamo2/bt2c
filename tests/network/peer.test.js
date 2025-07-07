/**
 * BT2C Peer Unit Tests
 * 
 * Tests the Peer class functionality for the BT2C network layer
 */

const { Peer, PeerState } = require('../../src/network/peer');

describe('Peer', () => {
  let peer;
  
  beforeEach(() => {
    // Create a new peer for each test
    peer = new Peer('test-peer-id', '127.0.0.1:26656');
  });
  
  test('should initialize with correct default values', () => {
    expect(peer.id).toBe('test-peer-id');
    expect(peer.address).toBe('127.0.0.1:26656');
    expect(peer.state).toBe(PeerState.DISCONNECTED);
    expect(peer.reputation).toBe(100);
    expect(peer.isValidator).toBe(false);
    expect(peer.messagesSent).toBe(0);
    expect(peer.messagesReceived).toBe(0);
  });
  
  test('should connect successfully', async () => {
    // Set up event listener to check for connected event
    const connectHandler = jest.fn();
    peer.on('connected', connectHandler);
    
    // Connect the peer
    const result = await peer.connect();
    
    // Check results
    expect(result).toBe(true);
    expect(peer.state).toBe(PeerState.CONNECTED);
    expect(connectHandler).toHaveBeenCalledWith(peer);
  });
  
  test('should disconnect successfully', async () => {
    // Set up event listener to check for disconnected event
    const disconnectHandler = jest.fn();
    peer.on('disconnected', disconnectHandler);
    
    // Connect and then disconnect the peer
    await peer.connect();
    peer.disconnect();
    
    // Check results
    expect(peer.state).toBe(PeerState.DISCONNECTED);
    expect(disconnectHandler).toHaveBeenCalledWith(peer);
  });
  
  test('should send messages when connected', async () => {
    // Set up event listener to check for message:sent event
    const messageSentHandler = jest.fn();
    peer.on('message:sent', messageSentHandler);
    
    // Connect the peer
    await peer.connect();
    
    // Send a message
    const result = peer.send('test_type', { test: 'data' });
    
    // Check results
    expect(result).toBe(true);
    expect(peer.messagesSent).toBe(1);
    expect(peer.bytesSent).toBeGreaterThan(0);
    expect(messageSentHandler).toHaveBeenCalled();
    expect(messageSentHandler.mock.calls[0][0].type).toBe('test_type');
    expect(messageSentHandler.mock.calls[0][0].data).toEqual({ test: 'data' });
  });
  
  test('should not send messages when disconnected', () => {
    // Try to send a message without connecting
    const result = peer.send('test_type', { test: 'data' });
    
    // Check results
    expect(result).toBe(false);
    expect(peer.messagesSent).toBe(0);
    expect(peer.bytesSent).toBe(0);
  });
  
  test('should receive messages when connected', async () => {
    // Set up event listener to check for message:received event
    const messageReceivedHandler = jest.fn();
    peer.on('message:received', messageReceivedHandler);
    
    // Connect the peer
    await peer.connect();
    
    // Simulate receiving a message
    const message = { type: 'test_type', data: { test: 'data' }, timestamp: Date.now() };
    peer.receive(message);
    
    // Check results
    expect(peer.messagesReceived).toBe(1);
    expect(peer.bytesReceived).toBeGreaterThan(0);
    expect(messageReceivedHandler).toHaveBeenCalledWith(message);
  });
  
  test('should not receive messages when disconnected', () => {
    // Set up event listener to check for message:received event
    const messageReceivedHandler = jest.fn();
    peer.on('message:received', messageReceivedHandler);
    
    // Simulate receiving a message without connecting
    const message = { type: 'test_type', data: { test: 'data' }, timestamp: Date.now() };
    peer.receive(message);
    
    // Check results
    expect(peer.messagesReceived).toBe(0);
    expect(peer.bytesReceived).toBe(0);
    expect(messageReceivedHandler).not.toHaveBeenCalled();
  });
  
  test('should update reputation correctly', () => {
    // Update reputation positively
    peer.updateReputation(10);
    expect(peer.reputation).toBe(110);
    
    // Update reputation negatively
    peer.updateReputation(-20);
    expect(peer.reputation).toBe(90);
    
    // Ensure reputation is capped at 200
    peer.updateReputation(200);
    expect(peer.reputation).toBe(200);
    
    // Ensure reputation is floored at 0
    peer.updateReputation(-300);
    expect(peer.reputation).toBe(0);
  });
  
  test('should ban peer when reputation reaches 0', () => {
    // Set up event listener to check for banned event
    const bannedHandler = jest.fn();
    peer.on('banned', bannedHandler);
    
    // Drop reputation to 0
    peer.updateReputation(-100);
    
    // Check results
    expect(peer.state).toBe(PeerState.BANNED);
    expect(peer.banUntil).toBeGreaterThan(Date.now());
    expect(bannedHandler).toHaveBeenCalledWith(peer);
  });
  
  test('should ban peer for specified duration', () => {
    // Ban the peer for 60 seconds
    const banDuration = 60;
    peer.ban(banDuration);
    
    // Check results
    expect(peer.state).toBe(PeerState.BANNED);
    expect(peer.banUntil).toBeGreaterThan(Date.now());
    expect(peer.banUntil).toBeLessThanOrEqual(Date.now() + (banDuration * 1000) + 100); // Add small buffer for test execution time
    
    // Check isBanned method
    expect(peer.isBanned()).toBe(true);
  });
  
  test('should update latency correctly', () => {
    peer.updateLatency(150);
    expect(peer.latency).toBe(150);
  });
  
  test('should update height correctly', () => {
    peer.updateHeight(1000);
    expect(peer.height).toBe(1000);
  });
  
  test('should check active status correctly', async () => {
    // Peer should not be active when disconnected
    expect(peer.isActive()).toBe(false);
    
    // Connect the peer
    await peer.connect();
    
    // Peer should be active when connected
    expect(peer.isActive()).toBe(true);
    
    // Mock lastSeen to be older than timeout
    const oldTime = Date.now() - 400000; // 400 seconds ago
    peer.lastSeen = oldTime;
    
    // Peer should not be active when last seen is older than timeout
    expect(peer.isActive()).toBe(false);
    
    // Peer should be active when using a longer timeout
    expect(peer.isActive(500000)).toBe(true);
  });
  
  test('should convert to and from JSON correctly', () => {
    // Set some values
    peer.version = '1.0.0';
    peer.height = 1000;
    peer.isValidator = true;
    peer.validatorAddress = 'validator-address';
    peer.latency = 150;
    
    // Convert to JSON
    const json = peer.toJSON();
    
    // Check JSON values
    expect(json.id).toBe('test-peer-id');
    expect(json.address).toBe('127.0.0.1:26656');
    expect(json.version).toBe('1.0.0');
    expect(json.height).toBe(1000);
    expect(json.isValidator).toBe(true);
    expect(json.validatorAddress).toBe('validator-address');
    expect(json.latency).toBe(150);
    
    // Create new peer from JSON
    const newPeer = Peer.fromJSON(json);
    
    // Check new peer values
    expect(newPeer.id).toBe('test-peer-id');
    expect(newPeer.address).toBe('127.0.0.1:26656');
    expect(newPeer.version).toBe('1.0.0');
    expect(newPeer.height).toBe(1000);
    expect(newPeer.isValidator).toBe(true);
    expect(newPeer.validatorAddress).toBe('validator-address');
    expect(newPeer.latency).toBe(150);
  });
});
