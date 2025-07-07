/**
 * BT2C Advanced Peer Scoring Implementation
 * 
 * This module provides advanced peer scoring and reputation management for the BT2C network layer.
 * It evaluates peers based on multiple factors including latency, uptime, block propagation,
 * transaction relay, validator status, and behavior patterns.
 */

const EventEmitter = require('events');

/**
 * Scoring categories for peer evaluation
 */
const ScoringCategory = {
  LATENCY: 'latency',
  UPTIME: 'uptime',
  BLOCK_PROPAGATION: 'block_propagation',
  TRANSACTION_RELAY: 'transaction_relay',
  VALIDATOR_STATUS: 'validator_status',
  BEHAVIOR: 'behavior'
};

/**
 * Peer behavior types for scoring
 */
const PeerBehavior = {
  GOOD_BLOCK: 'good_block',
  BAD_BLOCK: 'bad_block',
  GOOD_TRANSACTION: 'good_transaction',
  BAD_TRANSACTION: 'bad_transaction',
  SPAM: 'spam',
  INVALID_MESSAGE: 'invalid_message',
  TIMEOUT: 'timeout',
  DISCONNECT: 'disconnect',
  RECONNECT: 'reconnect',
  RELAY_SUCCESS: 'relay_success',
  RELAY_FAILURE: 'relay_failure'
};

/**
 * Advanced peer scoring class
 */
class PeerScoring extends EventEmitter {
  /**
   * Create a new PeerScoring instance
   * @param {Object} options - Scoring options
   * @param {Object} options.weights - Weights for different scoring categories
   * @param {Object} options.thresholds - Thresholds for different scoring actions
   * @param {number} options.decayPeriod - Period for score decay in milliseconds
   * @param {number} options.decayFactor - Factor for score decay (0-1)
   * @param {number} options.historySize - Size of behavior history to maintain
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      weights: {
        [ScoringCategory.LATENCY]: options.weights?.latency || 0.2,
        [ScoringCategory.UPTIME]: options.weights?.uptime || 0.2,
        [ScoringCategory.BLOCK_PROPAGATION]: options.weights?.blockPropagation || 0.25,
        [ScoringCategory.TRANSACTION_RELAY]: options.weights?.transactionRelay || 0.15,
        [ScoringCategory.VALIDATOR_STATUS]: options.weights?.validatorStatus || 0.1,
        [ScoringCategory.BEHAVIOR]: options.weights?.behavior || 0.1
      },
      thresholds: {
        ban: options.thresholds?.ban || -100,
        probation: options.thresholds?.probation || -50,
        disconnect: options.thresholds?.disconnect || -25,
        reconnect: options.thresholds?.reconnect || 25,
        trusted: options.thresholds?.trusted || 75
      },
      decayPeriod: options.decayPeriod || 3600000, // 1 hour
      decayFactor: options.decayFactor || 0.95, // 5% decay per period
      historySize: options.historySize || 100
    };
    
    this.peerScores = new Map();
    this.decayTimer = null;
    
    // Start decay timer
    this.startDecayTimer();
  }
  
  /**
   * Start the score decay timer
   */
  startDecayTimer() {
    this.stopDecayTimer();
    
    this.decayTimer = setInterval(() => {
      this.decayScores();
    }, this.options.decayPeriod);
  }
  
  /**
   * Stop the score decay timer
   */
  stopDecayTimer() {
    if (this.decayTimer) {
      clearInterval(this.decayTimer);
      this.decayTimer = null;
    }
  }
  
  /**
   * Initialize scoring for a peer
   * @param {string} peerId - ID of peer to initialize
   * @param {boolean} isValidator - Whether the peer is a validator
   */
  initPeer(peerId, isValidator = false) {
    if (this.peerScores.has(peerId)) {
      return;
    }
    
    const initialScore = isValidator ? 10 : 0;
    
    this.peerScores.set(peerId, {
      totalScore: initialScore,
      categories: {
        [ScoringCategory.LATENCY]: 0,
        [ScoringCategory.UPTIME]: 0,
        [ScoringCategory.BLOCK_PROPAGATION]: 0,
        [ScoringCategory.TRANSACTION_RELAY]: 0,
        [ScoringCategory.VALIDATOR_STATUS]: isValidator ? 10 : 0,
        [ScoringCategory.BEHAVIOR]: 0
      },
      metrics: {
        latency: [],
        uptime: {
          lastSeen: Date.now(),
          connectCount: 1,
          disconnectCount: 0,
          totalUptime: 0
        },
        blockPropagation: {
          received: 0,
          valid: 0,
          invalid: 0,
          propagationTimes: []
        },
        transactionRelay: {
          received: 0,
          valid: 0,
          invalid: 0,
          relayTimes: []
        }
      },
      history: [],
      isValidator,
      firstSeen: Date.now(),
      lastScoreUpdate: Date.now()
    });
    
    this.emit('peer:init', {
      peerId,
      score: initialScore,
      isValidator
    });
  }
  
  /**
   * Record peer behavior and update score
   * @param {string} peerId - ID of peer
   * @param {string} behavior - Behavior type from PeerBehavior
   * @param {Object} data - Additional behavior data
   * @returns {number} - New total score
   */
  recordBehavior(peerId, behavior, data = {}) {
    if (!this.peerScores.has(peerId)) {
      this.initPeer(peerId);
    }
    
    const peerScore = this.peerScores.get(peerId);
    let scoreChange = 0;
    
    // Calculate score change based on behavior
    switch (behavior) {
      case PeerBehavior.GOOD_BLOCK:
        scoreChange = 2;
        peerScore.metrics.blockPropagation.received++;
        peerScore.metrics.blockPropagation.valid++;
        if (data.propagationTime) {
          peerScore.metrics.blockPropagation.propagationTimes.push(data.propagationTime);
          // Keep only the last 50 propagation times
          if (peerScore.metrics.blockPropagation.propagationTimes.length > 50) {
            peerScore.metrics.blockPropagation.propagationTimes.shift();
          }
        }
        break;
        
      case PeerBehavior.BAD_BLOCK:
        scoreChange = -5;
        peerScore.metrics.blockPropagation.received++;
        peerScore.metrics.blockPropagation.invalid++;
        break;
        
      case PeerBehavior.GOOD_TRANSACTION:
        scoreChange = 1;
        peerScore.metrics.transactionRelay.received++;
        peerScore.metrics.transactionRelay.valid++;
        if (data.relayTime) {
          peerScore.metrics.transactionRelay.relayTimes.push(data.relayTime);
          // Keep only the last 100 relay times
          if (peerScore.metrics.transactionRelay.relayTimes.length > 100) {
            peerScore.metrics.transactionRelay.relayTimes.shift();
          }
        }
        break;
        
      case PeerBehavior.BAD_TRANSACTION:
        scoreChange = -2;
        peerScore.metrics.transactionRelay.received++;
        peerScore.metrics.transactionRelay.invalid++;
        break;
        
      case PeerBehavior.SPAM:
        scoreChange = -10;
        break;
        
      case PeerBehavior.INVALID_MESSAGE:
        scoreChange = -3;
        break;
        
      case PeerBehavior.TIMEOUT:
        scoreChange = -1;
        break;
        
      case PeerBehavior.DISCONNECT:
        scoreChange = -1;
        peerScore.metrics.uptime.disconnectCount++;
        peerScore.metrics.uptime.totalUptime += Date.now() - peerScore.metrics.uptime.lastSeen;
        break;
        
      case PeerBehavior.RECONNECT:
        scoreChange = 1;
        peerScore.metrics.uptime.connectCount++;
        peerScore.metrics.uptime.lastSeen = Date.now();
        break;
        
      case PeerBehavior.RELAY_SUCCESS:
        scoreChange = 1;
        break;
        
      case PeerBehavior.RELAY_FAILURE:
        scoreChange = -1;
        break;
    }
    
    // Update behavior history
    peerScore.history.unshift({
      behavior,
      scoreChange,
      timestamp: Date.now(),
      data
    });
    
    // Keep history at max size
    if (peerScore.history.length > this.options.historySize) {
      peerScore.history.pop();
    }
    
    // Update behavior category score
    peerScore.categories[ScoringCategory.BEHAVIOR] += scoreChange;
    
    // Update total score
    const oldScore = peerScore.totalScore;
    peerScore.totalScore = this.calculateTotalScore(peerId);
    peerScore.lastScoreUpdate = Date.now();
    
    // Save updated score
    this.peerScores.set(peerId, peerScore);
    
    // Check for threshold crossings
    this.checkThresholds(peerId, oldScore, peerScore.totalScore);
    
    this.emit('score:update', {
      peerId,
      behavior,
      scoreChange,
      newScore: peerScore.totalScore,
      category: ScoringCategory.BEHAVIOR
    });
    
    return peerScore.totalScore;
  }
  
  /**
   * Update peer latency score
   * @param {string} peerId - ID of peer
   * @param {number} latency - Latency in milliseconds
   * @returns {number} - New total score
   */
  updateLatency(peerId, latency) {
    if (!this.peerScores.has(peerId)) {
      this.initPeer(peerId);
    }
    
    const peerScore = this.peerScores.get(peerId);
    
    // Add latency to metrics
    peerScore.metrics.latency.push(latency);
    
    // Keep only the last 50 latency measurements
    if (peerScore.metrics.latency.length > 50) {
      peerScore.metrics.latency.shift();
    }
    
    // Calculate average latency
    const avgLatency = peerScore.metrics.latency.reduce((sum, val) => sum + val, 0) / 
                      peerScore.metrics.latency.length;
    
    // Score based on latency (lower is better)
    // <50ms: excellent, 50-100ms: good, 100-200ms: average, 200-500ms: poor, >500ms: bad
    let latencyScore = 0;
    if (avgLatency < 50) {
      latencyScore = 10;
    } else if (avgLatency < 100) {
      latencyScore = 8;
    } else if (avgLatency < 200) {
      latencyScore = 5;
    } else if (avgLatency < 500) {
      latencyScore = 2;
    } else {
      latencyScore = 0;
    }
    
    // Update latency category score
    const oldCategoryScore = peerScore.categories[ScoringCategory.LATENCY];
    peerScore.categories[ScoringCategory.LATENCY] = latencyScore;
    
    // Update total score
    const oldScore = peerScore.totalScore;
    peerScore.totalScore = this.calculateTotalScore(peerId);
    peerScore.lastScoreUpdate = Date.now();
    
    // Save updated score
    this.peerScores.set(peerId, peerScore);
    
    // Check for threshold crossings
    this.checkThresholds(peerId, oldScore, peerScore.totalScore);
    
    this.emit('score:update', {
      peerId,
      latency,
      scoreChange: peerScore.categories[ScoringCategory.LATENCY] - oldCategoryScore,
      newScore: peerScore.totalScore,
      category: ScoringCategory.LATENCY
    });
    
    return peerScore.totalScore;
  }
  
  /**
   * Update peer uptime score
   * @param {string} peerId - ID of peer
   * @param {boolean} isOnline - Whether the peer is currently online
   * @returns {number} - New total score
   */
  updateUptime(peerId, isOnline) {
    if (!this.peerScores.has(peerId)) {
      this.initPeer(peerId);
    }
    
    const peerScore = this.peerScores.get(peerId);
    
    // Update uptime metrics
    if (isOnline) {
      peerScore.metrics.uptime.lastSeen = Date.now();
    } else {
      peerScore.metrics.uptime.totalUptime += Date.now() - peerScore.metrics.uptime.lastSeen;
    }
    
    // Calculate uptime percentage
    const totalTime = Date.now() - peerScore.firstSeen;
    const uptimePercentage = (peerScore.metrics.uptime.totalUptime / totalTime) * 100;
    
    // Score based on uptime percentage
    let uptimeScore = 0;
    if (uptimePercentage > 99) {
      uptimeScore = 10;
    } else if (uptimePercentage > 95) {
      uptimeScore = 8;
    } else if (uptimePercentage > 90) {
      uptimeScore = 6;
    } else if (uptimePercentage > 80) {
      uptimeScore = 4;
    } else if (uptimePercentage > 70) {
      uptimeScore = 2;
    } else {
      uptimeScore = 0;
    }
    
    // Update uptime category score
    const oldCategoryScore = peerScore.categories[ScoringCategory.UPTIME];
    peerScore.categories[ScoringCategory.UPTIME] = uptimeScore;
    
    // Update total score
    const oldScore = peerScore.totalScore;
    peerScore.totalScore = this.calculateTotalScore(peerId);
    peerScore.lastScoreUpdate = Date.now();
    
    // Save updated score
    this.peerScores.set(peerId, peerScore);
    
    // Check for threshold crossings
    this.checkThresholds(peerId, oldScore, peerScore.totalScore);
    
    this.emit('score:update', {
      peerId,
      uptimePercentage,
      scoreChange: peerScore.categories[ScoringCategory.UPTIME] - oldCategoryScore,
      newScore: peerScore.totalScore,
      category: ScoringCategory.UPTIME
    });
    
    return peerScore.totalScore;
  }
  
  /**
   * Update peer block propagation score
   * @param {string} peerId - ID of peer
   * @returns {number} - New total score
   */
  updateBlockPropagation(peerId) {
    if (!this.peerScores.has(peerId)) {
      this.initPeer(peerId);
    }
    
    const peerScore = this.peerScores.get(peerId);
    
    // Skip if no blocks received
    if (peerScore.metrics.blockPropagation.received === 0) {
      return peerScore.totalScore;
    }
    
    // Calculate block validity ratio
    const validRatio = peerScore.metrics.blockPropagation.valid / 
                      peerScore.metrics.blockPropagation.received;
    
    // Calculate average propagation time if available
    let avgPropagationTime = 0;
    if (peerScore.metrics.blockPropagation.propagationTimes.length > 0) {
      avgPropagationTime = peerScore.metrics.blockPropagation.propagationTimes.reduce((sum, val) => sum + val, 0) / 
                          peerScore.metrics.blockPropagation.propagationTimes.length;
    }
    
    // Score based on validity ratio and propagation time
    let blockScore = 0;
    
    // Validity component (0-7 points)
    if (validRatio > 0.99) {
      blockScore += 7;
    } else if (validRatio > 0.95) {
      blockScore += 5;
    } else if (validRatio > 0.9) {
      blockScore += 3;
    } else if (validRatio > 0.8) {
      blockScore += 1;
    }
    
    // Propagation time component (0-3 points)
    if (peerScore.metrics.blockPropagation.propagationTimes.length > 0) {
      if (avgPropagationTime < 100) {
        blockScore += 3;
      } else if (avgPropagationTime < 300) {
        blockScore += 2;
      } else if (avgPropagationTime < 1000) {
        blockScore += 1;
      }
    }
    
    // Update block propagation category score
    const oldCategoryScore = peerScore.categories[ScoringCategory.BLOCK_PROPAGATION];
    peerScore.categories[ScoringCategory.BLOCK_PROPAGATION] = blockScore;
    
    // Update total score
    const oldScore = peerScore.totalScore;
    peerScore.totalScore = this.calculateTotalScore(peerId);
    peerScore.lastScoreUpdate = Date.now();
    
    // Save updated score
    this.peerScores.set(peerId, peerScore);
    
    // Check for threshold crossings
    this.checkThresholds(peerId, oldScore, peerScore.totalScore);
    
    this.emit('score:update', {
      peerId,
      validRatio,
      avgPropagationTime,
      scoreChange: peerScore.categories[ScoringCategory.BLOCK_PROPAGATION] - oldCategoryScore,
      newScore: peerScore.totalScore,
      category: ScoringCategory.BLOCK_PROPAGATION
    });
    
    return peerScore.totalScore;
  }
  
  /**
   * Update peer transaction relay score
   * @param {string} peerId - ID of peer
   * @returns {number} - New total score
   */
  updateTransactionRelay(peerId) {
    if (!this.peerScores.has(peerId)) {
      this.initPeer(peerId);
    }
    
    const peerScore = this.peerScores.get(peerId);
    
    // Skip if no transactions received
    if (peerScore.metrics.transactionRelay.received === 0) {
      return peerScore.totalScore;
    }
    
    // Calculate transaction validity ratio
    const validRatio = peerScore.metrics.transactionRelay.valid / 
                      peerScore.metrics.transactionRelay.received;
    
    // Calculate average relay time if available
    let avgRelayTime = 0;
    if (peerScore.metrics.transactionRelay.relayTimes.length > 0) {
      avgRelayTime = peerScore.metrics.transactionRelay.relayTimes.reduce((sum, val) => sum + val, 0) / 
                    peerScore.metrics.transactionRelay.relayTimes.length;
    }
    
    // Score based on validity ratio and relay time
    let txScore = 0;
    
    // Validity component (0-7 points)
    if (validRatio > 0.99) {
      txScore += 7;
    } else if (validRatio > 0.95) {
      txScore += 5;
    } else if (validRatio > 0.9) {
      txScore += 3;
    } else if (validRatio > 0.8) {
      txScore += 1;
    }
    
    // Relay time component (0-3 points)
    if (peerScore.metrics.transactionRelay.relayTimes.length > 0) {
      if (avgRelayTime < 50) {
        txScore += 3;
      } else if (avgRelayTime < 150) {
        txScore += 2;
      } else if (avgRelayTime < 500) {
        txScore += 1;
      }
    }
    
    // Update transaction relay category score
    const oldCategoryScore = peerScore.categories[ScoringCategory.TRANSACTION_RELAY];
    peerScore.categories[ScoringCategory.TRANSACTION_RELAY] = txScore;
    
    // Update total score
    const oldScore = peerScore.totalScore;
    peerScore.totalScore = this.calculateTotalScore(peerId);
    peerScore.lastScoreUpdate = Date.now();
    
    // Save updated score
    this.peerScores.set(peerId, peerScore);
    
    // Check for threshold crossings
    this.checkThresholds(peerId, oldScore, peerScore.totalScore);
    
    this.emit('score:update', {
      peerId,
      validRatio,
      avgRelayTime,
      scoreChange: peerScore.categories[ScoringCategory.TRANSACTION_RELAY] - oldCategoryScore,
      newScore: peerScore.totalScore,
      category: ScoringCategory.TRANSACTION_RELAY
    });
    
    return peerScore.totalScore;
  }
  
  /**
   * Update peer validator status
   * @param {string} peerId - ID of peer
   * @param {boolean} isValidator - Whether the peer is a validator
   * @returns {number} - New total score
   */
  updateValidatorStatus(peerId, isValidator) {
    if (!this.peerScores.has(peerId)) {
      this.initPeer(peerId, isValidator);
      return this.peerScores.get(peerId).totalScore;
    }
    
    const peerScore = this.peerScores.get(peerId);
    
    // Update validator status
    peerScore.isValidator = isValidator;
    
    // Update validator status category score
    const oldCategoryScore = peerScore.categories[ScoringCategory.VALIDATOR_STATUS];
    peerScore.categories[ScoringCategory.VALIDATOR_STATUS] = isValidator ? 10 : 0;
    
    // Update total score
    const oldScore = peerScore.totalScore;
    peerScore.totalScore = this.calculateTotalScore(peerId);
    peerScore.lastScoreUpdate = Date.now();
    
    // Save updated score
    this.peerScores.set(peerId, peerScore);
    
    // Check for threshold crossings
    this.checkThresholds(peerId, oldScore, peerScore.totalScore);
    
    this.emit('score:update', {
      peerId,
      isValidator,
      scoreChange: peerScore.categories[ScoringCategory.VALIDATOR_STATUS] - oldCategoryScore,
      newScore: peerScore.totalScore,
      category: ScoringCategory.VALIDATOR_STATUS
    });
    
    return peerScore.totalScore;
  }
  
  /**
   * Calculate total score for a peer
   * @param {string} peerId - ID of peer
   * @returns {number} - Total score
   */
  calculateTotalScore(peerId) {
    if (!this.peerScores.has(peerId)) {
      return 0;
    }
    
    const peerScore = this.peerScores.get(peerId);
    let totalScore = 0;
    
    // Calculate weighted sum of category scores
    for (const [category, weight] of Object.entries(this.options.weights)) {
      totalScore += peerScore.categories[category] * weight;
    }
    
    // Ensure score is within bounds (-100 to 100)
    return Math.max(-100, Math.min(100, totalScore));
  }
  
  /**
   * Check if score crosses any thresholds
   * @param {string} peerId - ID of peer
   * @param {number} oldScore - Old total score
   * @param {number} newScore - New total score
   */
  checkThresholds(peerId, oldScore, newScore) {
    const thresholds = this.options.thresholds;
    
    // Check ban threshold
    if (oldScore > thresholds.ban && newScore <= thresholds.ban) {
      this.emit('threshold:ban', {
        peerId,
        score: newScore,
        threshold: thresholds.ban
      });
    }
    
    // Check probation threshold
    if (oldScore > thresholds.probation && newScore <= thresholds.probation) {
      this.emit('threshold:probation', {
        peerId,
        score: newScore,
        threshold: thresholds.probation
      });
    }
    
    // Check disconnect threshold
    if (oldScore > thresholds.disconnect && newScore <= thresholds.disconnect) {
      this.emit('threshold:disconnect', {
        peerId,
        score: newScore,
        threshold: thresholds.disconnect
      });
    }
    
    // Check reconnect threshold
    if (oldScore < thresholds.reconnect && newScore >= thresholds.reconnect) {
      this.emit('threshold:reconnect', {
        peerId,
        score: newScore,
        threshold: thresholds.reconnect
      });
    }
    
    // Check trusted threshold
    if (oldScore < thresholds.trusted && newScore >= thresholds.trusted) {
      this.emit('threshold:trusted', {
        peerId,
        score: newScore,
        threshold: thresholds.trusted
      });
    }
  }
  
  /**
   * Decay scores for all peers
   */
  decayScores() {
    for (const [peerId, peerScore] of this.peerScores.entries()) {
      // Skip if score was updated recently
      if (Date.now() - peerScore.lastScoreUpdate < this.options.decayPeriod) {
        continue;
      }
      
      const oldScore = peerScore.totalScore;
      
      // Decay behavior score towards 0
      if (peerScore.categories[ScoringCategory.BEHAVIOR] !== 0) {
        const direction = peerScore.categories[ScoringCategory.BEHAVIOR] > 0 ? -1 : 1;
        const decayAmount = Math.max(1, Math.abs(peerScore.categories[ScoringCategory.BEHAVIOR] * (1 - this.options.decayFactor)));
        peerScore.categories[ScoringCategory.BEHAVIOR] += direction * decayAmount;
        
        // Ensure it doesn't cross 0
        if ((direction === -1 && peerScore.categories[ScoringCategory.BEHAVIOR] < 0) ||
            (direction === 1 && peerScore.categories[ScoringCategory.BEHAVIOR] > 0)) {
          peerScore.categories[ScoringCategory.BEHAVIOR] = 0;
        }
      }
      
      // Recalculate total score
      peerScore.totalScore = this.calculateTotalScore(peerId);
      peerScore.lastScoreUpdate = Date.now();
      
      // Save updated score
      this.peerScores.set(peerId, peerScore);
      
      // Check for threshold crossings
      this.checkThresholds(peerId, oldScore, peerScore.totalScore);
      
      this.emit('score:decay', {
        peerId,
        oldScore,
        newScore: peerScore.totalScore
      });
    }
  }
  
  /**
   * Get score for a peer
   * @param {string} peerId - ID of peer
   * @returns {Object|null} - Peer score object or null if not found
   */
  getScore(peerId) {
    if (!this.peerScores.has(peerId)) {
      return null;
    }
    
    return { ...this.peerScores.get(peerId) };
  }
  
  /**
   * Get total score for a peer
   * @param {string} peerId - ID of peer
   * @returns {number} - Total score or 0 if not found
   */
  getTotalScore(peerId) {
    if (!this.peerScores.has(peerId)) {
      return 0;
    }
    
    return this.peerScores.get(peerId).totalScore;
  }
  
  /**
   * Get all peer scores
   * @returns {Map} - Map of peer scores
   */
  getAllScores() {
    return new Map(this.peerScores);
  }
  
  /**
   * Get top scoring peers
   * @param {number} limit - Maximum number of peers to return
   * @returns {Array} - Array of peer score objects
   */
  getTopPeers(limit = 10) {
    return Array.from(this.peerScores.entries())
      .sort((a, b) => b[1].totalScore - a[1].totalScore)
      .slice(0, limit)
      .map(([peerId, score]) => ({
        peerId,
        ...score
      }));
  }
  
  /**
   * Reset score for a peer
   * @param {string} peerId - ID of peer
   * @param {boolean} isValidator - Whether the peer is a validator
   */
  resetScore(peerId, isValidator = false) {
    this.peerScores.delete(peerId);
    this.initPeer(peerId, isValidator);
    
    this.emit('score:reset', {
      peerId,
      isValidator
    });
  }
  
  /**
   * Close the peer scoring service
   */
  close() {
    this.stopDecayTimer();
    this.peerScores.clear();
  }
}

module.exports = {
  PeerScoring,
  ScoringCategory,
  PeerBehavior
};
