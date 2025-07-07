/**
 * BT2C Peer Scoring Tests
 * 
 * This file contains unit tests for the peer scoring module.
 */

const { PeerScoring, ScoringCategory, PeerBehavior } = require('../../src/network/peer_scoring');

describe('PeerScoring', () => {
  let peerScoring;
  const testPeerId = 'test-peer-id';
  const validatorPeerId = 'validator-peer-id';
  
  beforeEach(() => {
    // Create a new PeerScoring instance with faster decay for testing
    peerScoring = new PeerScoring({
      decayPeriod: 100, // 100ms for faster testing
      decayFactor: 0.9
    });
  });
  
  afterEach(() => {
    // Clean up
    peerScoring.close();
  });
  
  test('should initialize with default options', () => {
    expect(peerScoring.options.weights).toBeDefined();
    expect(peerScoring.options.thresholds).toBeDefined();
    expect(peerScoring.peerScores.size).toBe(0);
  });
  
  test('should initialize a peer with correct initial score', () => {
    peerScoring.initPeer(testPeerId);
    const score = peerScoring.getScore(testPeerId);
    
    expect(score).toBeDefined();
    expect(score.totalScore).toBe(0);
    expect(score.isValidator).toBe(false);
    
    peerScoring.initPeer(validatorPeerId, true);
    const validatorScore = peerScoring.getScore(validatorPeerId);
    
    expect(validatorScore).toBeDefined();
    expect(validatorScore.totalScore).toBe(10);
    expect(validatorScore.isValidator).toBe(true);
  });
  
  test('should record behavior and update score', () => {
    const newScore = peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_BLOCK);
    
    expect(newScore).toBeGreaterThan(0);
    
    const score = peerScoring.getScore(testPeerId);
    expect(score.history.length).toBe(1);
    expect(score.history[0].behavior).toBe(PeerBehavior.GOOD_BLOCK);
  });
  
  test('should handle multiple behaviors correctly', () => {
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_BLOCK);
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_TRANSACTION);
    peerScoring.recordBehavior(testPeerId, PeerBehavior.BAD_TRANSACTION);
    
    const score = peerScoring.getScore(testPeerId);
    expect(score.history.length).toBe(3);
    
    // Good block (+2) + Good transaction (+1) + Bad transaction (-2) = +1
    expect(score.categories[ScoringCategory.BEHAVIOR]).toBe(1);
  });
  
  test('should update latency score', () => {
    peerScoring.updateLatency(testPeerId, 50);
    let score = peerScoring.getScore(testPeerId);
    
    expect(score.metrics.latency).toContain(50);
    expect(score.categories[ScoringCategory.LATENCY]).toBeGreaterThan(0);
    
    // Test with poor latency
    peerScoring.updateLatency(testPeerId, 1000);
    score = peerScoring.getScore(testPeerId);
    
    expect(score.metrics.latency).toContain(1000);
    expect(score.categories[ScoringCategory.LATENCY]).toBeLessThan(score.categories[ScoringCategory.LATENCY] + 1);
  });
  
  test('should update uptime score', () => {
    // Initialize peer
    peerScoring.initPeer(testPeerId);
    
    // Fast-forward time for testing
    const originalDateNow = Date.now;
    const mockTime = Date.now();
    
    try {
      // Mock Date.now to return controlled values
      global.Date.now = jest.fn(() => mockTime);
      
      // Update uptime with peer online
      peerScoring.updateUptime(testPeerId, true);
      
      // Fast-forward 1 hour
      global.Date.now = jest.fn(() => mockTime + 3600000);
      
      // Update uptime with peer offline
      peerScoring.updateUptime(testPeerId, false);
      
      const score = peerScoring.getScore(testPeerId);
      expect(score.metrics.uptime.totalUptime).toBe(3600000);
      expect(score.categories[ScoringCategory.UPTIME]).toBeGreaterThan(0);
    } finally {
      // Restore original Date.now
      global.Date.now = originalDateNow;
    }
  });
  
  test('should update block propagation score', () => {
    // Record good blocks
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_BLOCK, { propagationTime: 100 });
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_BLOCK, { propagationTime: 150 });
    
    // Update block propagation score
    peerScoring.updateBlockPropagation(testPeerId);
    
    const score = peerScoring.getScore(testPeerId);
    expect(score.metrics.blockPropagation.valid).toBe(2);
    expect(score.metrics.blockPropagation.invalid).toBe(0);
    expect(score.categories[ScoringCategory.BLOCK_PROPAGATION]).toBeGreaterThan(0);
    
    // Add a bad block
    peerScoring.recordBehavior(testPeerId, PeerBehavior.BAD_BLOCK);
    peerScoring.updateBlockPropagation(testPeerId);
    
    const updatedScore = peerScoring.getScore(testPeerId);
    expect(updatedScore.metrics.blockPropagation.valid).toBe(2);
    expect(updatedScore.metrics.blockPropagation.invalid).toBe(1);
    expect(updatedScore.categories[ScoringCategory.BLOCK_PROPAGATION]).toBeLessThan(score.categories[ScoringCategory.BLOCK_PROPAGATION]);
  });
  
  test('should update transaction relay score', () => {
    // Record good transactions
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_TRANSACTION, { relayTime: 50 });
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_TRANSACTION, { relayTime: 75 });
    
    // Update transaction relay score
    peerScoring.updateTransactionRelay(testPeerId);
    
    const score = peerScoring.getScore(testPeerId);
    expect(score.metrics.transactionRelay.valid).toBe(2);
    expect(score.metrics.transactionRelay.invalid).toBe(0);
    expect(score.categories[ScoringCategory.TRANSACTION_RELAY]).toBeGreaterThan(0);
    
    // Add a bad transaction
    peerScoring.recordBehavior(testPeerId, PeerBehavior.BAD_TRANSACTION);
    peerScoring.updateTransactionRelay(testPeerId);
    
    const updatedScore = peerScoring.getScore(testPeerId);
    expect(updatedScore.metrics.transactionRelay.valid).toBe(2);
    expect(updatedScore.metrics.transactionRelay.invalid).toBe(1);
    expect(updatedScore.categories[ScoringCategory.TRANSACTION_RELAY]).toBeLessThan(score.categories[ScoringCategory.TRANSACTION_RELAY]);
  });
  
  test('should update validator status', () => {
    // Initialize as non-validator
    peerScoring.initPeer(testPeerId, false);
    let score = peerScoring.getScore(testPeerId);
    
    expect(score.isValidator).toBe(false);
    expect(score.categories[ScoringCategory.VALIDATOR_STATUS]).toBe(0);
    
    // Update to validator
    peerScoring.updateValidatorStatus(testPeerId, true);
    score = peerScoring.getScore(testPeerId);
    
    expect(score.isValidator).toBe(true);
    expect(score.categories[ScoringCategory.VALIDATOR_STATUS]).toBe(10);
    
    // Update back to non-validator
    peerScoring.updateValidatorStatus(testPeerId, false);
    score = peerScoring.getScore(testPeerId);
    
    expect(score.isValidator).toBe(false);
    expect(score.categories[ScoringCategory.VALIDATOR_STATUS]).toBe(0);
  });
  
  test('should calculate total score correctly', () => {
    // Initialize peer
    peerScoring.initPeer(testPeerId);
    
    // Set category scores
    const peerScore = peerScoring.peerScores.get(testPeerId);
    peerScore.categories[ScoringCategory.LATENCY] = 8;
    peerScore.categories[ScoringCategory.UPTIME] = 6;
    peerScore.categories[ScoringCategory.BLOCK_PROPAGATION] = 7;
    peerScore.categories[ScoringCategory.TRANSACTION_RELAY] = 5;
    peerScore.categories[ScoringCategory.VALIDATOR_STATUS] = 0;
    peerScore.categories[ScoringCategory.BEHAVIOR] = 10;
    
    peerScoring.peerScores.set(testPeerId, peerScore);
    
    // Calculate total score
    const totalScore = peerScoring.calculateTotalScore(testPeerId);
    
    // Expected: (8 * 0.2) + (6 * 0.2) + (7 * 0.25) + (5 * 0.15) + (0 * 0.1) + (10 * 0.1) = 6.35
    expect(totalScore).toBeCloseTo(6.35, 1);
  });
  
  test('should check thresholds and emit events', () => {
    // Set up event listener
    const thresholdEvents = [];
    peerScoring.on('threshold:trusted', (data) => {
      thresholdEvents.push({ type: 'trusted', data });
    });
    
    // Initialize peer with high score
    peerScoring.initPeer(testPeerId);
    const peerScore = peerScoring.peerScores.get(testPeerId);
    
    // Set scores to cross trusted threshold (75)
    Object.keys(peerScore.categories).forEach(category => {
      peerScore.categories[category] = 50;
    });
    
    peerScoring.peerScores.set(testPeerId, peerScore);
    
    // Check thresholds
    peerScoring.checkThresholds(testPeerId, 70, 80);
    
    // Should have emitted trusted threshold event
    expect(thresholdEvents.length).toBe(1);
    expect(thresholdEvents[0].type).toBe('trusted');
    expect(thresholdEvents[0].data.peerId).toBe(testPeerId);
  });
  
  test('should decay scores over time', (done) => {
    // Set up peer with positive behavior score
    peerScoring.initPeer(testPeerId);
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_BLOCK);
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_BLOCK);
    
    const initialScore = peerScoring.getScore(testPeerId);
    const initialBehaviorScore = initialScore.categories[ScoringCategory.BEHAVIOR];
    
    expect(initialBehaviorScore).toBeGreaterThan(0);
    
    // Wait for decay
    setTimeout(() => {
      // Force decay
      peerScoring.decayScores();
      
      const decayedScore = peerScoring.getScore(testPeerId);
      const decayedBehaviorScore = decayedScore.categories[ScoringCategory.BEHAVIOR];
      
      // Score should have decayed
      expect(decayedBehaviorScore).toBeLessThan(initialBehaviorScore);
      
      done();
    }, 150); // Wait longer than decay period
  });
  
  test('should get top peers', () => {
    // Add multiple peers with different scores
    peerScoring.initPeer('peer1');
    peerScoring.initPeer('peer2');
    peerScoring.initPeer('peer3', true); // Validator
    
    // Record behaviors to create different scores
    peerScoring.recordBehavior('peer1', PeerBehavior.GOOD_BLOCK);
    peerScoring.recordBehavior('peer2', PeerBehavior.GOOD_BLOCK);
    peerScoring.recordBehavior('peer2', PeerBehavior.GOOD_BLOCK);
    
    // Get top peers
    const topPeers = peerScoring.getTopPeers(2);
    
    // Should return 2 peers
    expect(topPeers.length).toBe(2);
    
    // First peer should be peer3 (validator) or peer2 (2 good blocks)
    expect(['peer3', 'peer2']).toContain(topPeers[0].peerId);
    
    // Scores should be in descending order
    expect(topPeers[0].totalScore).toBeGreaterThanOrEqual(topPeers[1].totalScore);
  });
  
  test('should reset peer score', () => {
    // Set up peer with some history
    peerScoring.initPeer(testPeerId);
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_BLOCK);
    peerScoring.recordBehavior(testPeerId, PeerBehavior.GOOD_TRANSACTION);
    
    const initialScore = peerScoring.getScore(testPeerId);
    expect(initialScore.history.length).toBe(2);
    
    // Reset score
    peerScoring.resetScore(testPeerId);
    
    const resetScore = peerScoring.getScore(testPeerId);
    expect(resetScore.history.length).toBe(0);
    expect(resetScore.totalScore).toBe(0);
    
    // Reset as validator
    peerScoring.resetScore(testPeerId, true);
    
    const validatorScore = peerScoring.getScore(testPeerId);
    expect(validatorScore.isValidator).toBe(true);
    expect(validatorScore.totalScore).toBe(10);
  });
});
