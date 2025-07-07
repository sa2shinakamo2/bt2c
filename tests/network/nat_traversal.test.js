/**
 * BT2C NAT Traversal Tests
 * 
 * This file contains unit tests for the NAT traversal module.
 */

const { NATTraversal, TraversalMethod } = require('../../src/network/nat_traversal');

// Mock the stun and turn clients
jest.mock('stun', () => ({
  createClient: jest.fn().mockReturnValue({
    request: jest.fn((server, callback) => {
      callback(null, {
        getXorAddress: () => ({ address: '123.45.67.89', port: 12345 })
      });
    })
  })
}));

jest.mock('node-turn', () => ({
  createClient: jest.fn().mockReturnValue({
    allocate: jest.fn((options, callback) => {
      callback(null, { relayedAddress: '98.76.54.32', relayedPort: 54321 });
    }),
    on: jest.fn(),
    close: jest.fn()
  })
}));

describe('NATTraversal', () => {
  let natTraversal;
  
  beforeEach(() => {
    // Create a new NATTraversal instance
    natTraversal = new NATTraversal({
      stunServers: ['stun:stun.example.com:3478'],
      turnServers: [{
        urls: 'turn:turn.example.com:3478',
        username: 'testuser',
        credential: 'testpass'
      }]
    });
  });
  
  afterEach(() => {
    // Clean up
    natTraversal.close();
  });
  
  test('should initialize with default options', () => {
    const defaultNAT = new NATTraversal();
    expect(defaultNAT.options.stunServers).toBeDefined();
    expect(defaultNAT.options.turnServers).toBeDefined();
    expect(defaultNAT.options.preferredMethod).toBe(TraversalMethod.STUN);
  });
  
  test('should discover external IP using STUN', async () => {
    const result = await natTraversal.discoverExternalAddress(TraversalMethod.STUN);
    
    expect(result).toBeDefined();
    expect(result.address).toBe('123.45.67.89');
    expect(result.port).toBe(12345);
    expect(result.method).toBe(TraversalMethod.STUN);
  });
  
  test('should allocate relay using TURN', async () => {
    const result = await natTraversal.allocateRelay();
    
    expect(result).toBeDefined();
    expect(result.address).toBe('98.76.54.32');
    expect(result.port).toBe(54321);
    expect(result.method).toBe(TraversalMethod.TURN);
  });
  
  test('should discover address with preferred method', async () => {
    // Set preferred method to STUN
    natTraversal.options.preferredMethod = TraversalMethod.STUN;
    
    const result = await natTraversal.discoverAddress();
    
    expect(result.method).toBe(TraversalMethod.STUN);
    expect(result.address).toBe('123.45.67.89');
    
    // Set preferred method to TURN
    natTraversal.options.preferredMethod = TraversalMethod.TURN;
    
    const turnResult = await natTraversal.discoverAddress();
    
    expect(turnResult.method).toBe(TraversalMethod.TURN);
    expect(turnResult.address).toBe('98.76.54.32');
  });
  
  test('should fall back to alternative method if preferred fails', async () => {
    // Mock STUN failure
    const stun = require('stun');
    stun.createClient.mockReturnValueOnce({
      request: jest.fn((server, callback) => {
        callback(new Error('STUN request failed'), null);
      })
    });
    
    // Set preferred method to STUN (which will fail)
    natTraversal.options.preferredMethod = TraversalMethod.STUN;
    
    const result = await natTraversal.discoverAddress();
    
    // Should fall back to TURN
    expect(result.method).toBe(TraversalMethod.TURN);
    expect(result.address).toBe('98.76.54.32');
  });
  
  test('should handle errors in STUN discovery', async () => {
    // Mock STUN failure
    const stun = require('stun');
    stun.createClient.mockReturnValueOnce({
      request: jest.fn((server, callback) => {
        callback(new Error('STUN request failed'), null);
      })
    });
    
    try {
      await natTraversal.discoverExternalAddress(TraversalMethod.STUN);
      fail('Should have thrown an error');
    } catch (error) {
      expect(error.message).toContain('Failed to discover external address using STUN');
    }
  });
  
  test('should handle errors in TURN allocation', async () => {
    // Mock TURN failure
    const nodeTurn = require('node-turn');
    nodeTurn.createClient.mockReturnValueOnce({
      allocate: jest.fn((options, callback) => {
        callback(new Error('TURN allocation failed'), null);
      }),
      on: jest.fn(),
      close: jest.fn()
    });
    
    try {
      await natTraversal.allocateRelay();
      fail('Should have thrown an error');
    } catch (error) {
      expect(error.message).toContain('Failed to allocate TURN relay');
    }
  });
  
  test('should create connection candidates', async () => {
    // Mock successful discovery
    natTraversal.discoverExternalAddress = jest.fn().mockResolvedValue({
      address: '123.45.67.89',
      port: 12345,
      method: TraversalMethod.STUN
    });
    
    natTraversal.allocateRelay = jest.fn().mockResolvedValue({
      address: '98.76.54.32',
      port: 54321,
      method: TraversalMethod.TURN
    });
    
    const candidates = await natTraversal.createConnectionCandidates({
      localAddress: '192.168.1.100',
      localPort: 8080
    });
    
    expect(candidates).toBeDefined();
    expect(candidates.length).toBe(3);
    
    // Check local candidate
    expect(candidates[0].type).toBe('host');
    expect(candidates[0].address).toBe('192.168.1.100');
    expect(candidates[0].port).toBe(8080);
    
    // Check STUN candidate
    expect(candidates[1].type).toBe('srflx');
    expect(candidates[1].address).toBe('123.45.67.89');
    expect(candidates[1].port).toBe(12345);
    
    // Check TURN candidate
    expect(candidates[2].type).toBe('relay');
    expect(candidates[2].address).toBe('98.76.54.32');
    expect(candidates[2].port).toBe(54321);
  });
  
  test('should handle connection candidate creation errors', async () => {
    // Mock discovery failures
    natTraversal.discoverExternalAddress = jest.fn().mockRejectedValue(
      new Error('STUN discovery failed')
    );
    
    natTraversal.allocateRelay = jest.fn().mockRejectedValue(
      new Error('TURN allocation failed')
    );
    
    const candidates = await natTraversal.createConnectionCandidates({
      localAddress: '192.168.1.100',
      localPort: 8080
    });
    
    // Should still return local candidate
    expect(candidates).toBeDefined();
    expect(candidates.length).toBe(1);
    expect(candidates[0].type).toBe('host');
    expect(candidates[0].address).toBe('192.168.1.100');
  });
  
  test('should select best candidate', () => {
    const candidates = [
      { type: 'host', address: '192.168.1.100', port: 8080, priority: 1 },
      { type: 'srflx', address: '123.45.67.89', port: 12345, priority: 2 },
      { type: 'relay', address: '98.76.54.32', port: 54321, priority: 3 }
    ];
    
    // Test with different preferences
    natTraversal.options.candidatePreference = 'host';
    let selected = natTraversal.selectBestCandidate(candidates);
    expect(selected.type).toBe('host');
    
    natTraversal.options.candidatePreference = 'srflx';
    selected = natTraversal.selectBestCandidate(candidates);
    expect(selected.type).toBe('srflx');
    
    natTraversal.options.candidatePreference = 'relay';
    selected = natTraversal.selectBestCandidate(candidates);
    expect(selected.type).toBe('relay');
    
    // Test with priority preference
    natTraversal.options.candidatePreference = 'priority';
    selected = natTraversal.selectBestCandidate(candidates);
    expect(selected.priority).toBe(3);
  });
  
  test('should close and clean up resources', () => {
    // Create mock TURN client
    const turnClient = {
      close: jest.fn(),
      on: jest.fn()
    };
    
    natTraversal.turnClient = turnClient;
    
    // Close NAT traversal
    natTraversal.close();
    
    // Verify TURN client was closed
    expect(turnClient.close).toHaveBeenCalled();
    
    // Verify turnClient was cleared
    expect(natTraversal.turnClient).toBeNull();
  });
});
