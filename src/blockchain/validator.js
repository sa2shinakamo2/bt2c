/**
 * BT2C Validator Structure
 * 
 * Implements the validator data structure for BT2C including:
 * - Validator states (Active, Inactive, Jailed, Tombstoned)
 * - Reputation scoring
 * - Validator selection probability calculation
 */

/**
 * Validator states enum
 * @enum {string}
 */
const ValidatorState = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  JAILED: 'jailed',
  TOMBSTONED: 'tombstoned'
};

/**
 * Validator class representing a BT2C validator
 */
class Validator {
  /**
   * Create a new validator
   * @param {string} address - Validator's address
   * @param {string} publicKey - Validator's public key
   * @param {number} stake - Validator's staked amount
   * @param {string} moniker - Validator's name/moniker
   */
  constructor(address, publicKey, stake, moniker) {
    this.address = address;
    this.publicKey = publicKey;
    this.stake = stake;
    this.moniker = moniker;
    this.state = ValidatorState.INACTIVE;
    this.reputation = 100; // Initial reputation score (0-200)
    this.blocksProduced = 0;
    this.blocksValidated = 0;
    this.blocksMissed = 0;
    this.uptime = 100; // Percentage
    this.lastActive = Date.now();
    this.jailedUntil = 0;
    this.isFirstValidator = false; // Developer node flag
    this.joinedDuringDistribution = false; // Early validator flag
    this.distributionRewardClaimed = false;
  }

  /**
   * Calculate the selection probability based on stake and reputation
   * @param {number} totalStake - Total stake in the network
   * @returns {number} Selection probability
   */
  calculateSelectionProbability(totalStake) {
    // Base probability based on stake percentage
    const stakeProbability = this.stake / totalStake;
    
    // Reputation multiplier (0.5x to 2.0x)
    const reputationMultiplier = 0.5 + (this.reputation / 133.33);
    
    // Final probability (stake-weighted and reputation-adjusted)
    return stakeProbability * reputationMultiplier;
  }

  /**
   * Update reputation score based on performance
   * @param {boolean} producedBlock - Whether the validator produced their assigned block
   * @param {number} validationAccuracy - Percentage of correct validations
   * @param {number} currentUptime - Current uptime percentage
   */
  updateReputation(producedBlock, validationAccuracy, currentUptime) {
    // Start with current reputation
    let newReputation = this.reputation;
    
    // Adjust for block production
    if (producedBlock) {
      newReputation += 1;
    } else {
      newReputation -= 5;
    }
    
    // Adjust for validation accuracy
    newReputation += (validationAccuracy - 95) / 5;
    
    // Adjust for uptime
    newReputation += (currentUptime - 95) / 5;
    
    // Ensure reputation stays within bounds (0-200)
    this.reputation = Math.max(0, Math.min(200, newReputation));
  }

  /**
   * Jail the validator for missing blocks
   * @param {number} duration - Jail duration in seconds
   */
  jail(duration) {
    this.state = ValidatorState.JAILED;
    this.jailedUntil = Date.now() + (duration * 1000);
    this.reputation = Math.max(0, this.reputation - 20);
  }

  /**
   * Unjail the validator if jail period is over
   * @returns {boolean} True if validator was unjailed
   */
  tryUnjail() {
    if (this.state === ValidatorState.JAILED && Date.now() > this.jailedUntil) {
      this.state = ValidatorState.INACTIVE;
      return true;
    }
    return false;
  }

  /**
   * Tombstone the validator for severe violations
   */
  tombstone() {
    this.state = ValidatorState.TOMBSTONED;
    this.reputation = 0;
  }

  /**
   * Activate the validator
   * @returns {boolean} True if activation was successful
   */
  activate() {
    if (this.state === ValidatorState.INACTIVE) {
      this.state = ValidatorState.ACTIVE;
      this.lastActive = Date.now();
      return true;
    }
    return false;
  }

  /**
   * Deactivate the validator
   */
  deactivate() {
    if (this.state === ValidatorState.ACTIVE) {
      this.state = ValidatorState.INACTIVE;
    }
  }

  /**
   * Check if validator is eligible for selection
   * @returns {boolean} True if validator is eligible
   */
  isEligible() {
    return this.state === ValidatorState.ACTIVE && this.stake >= 1.0;
  }

  /**
   * Update validator statistics after block production
   * @param {boolean} produced - Whether the validator produced their assigned block
   */
  updateStats(produced) {
    if (produced) {
      this.blocksProduced++;
    } else {
      this.blocksMissed++;
    }
    
    // Update uptime (simplified calculation)
    const totalBlocks = this.blocksProduced + this.blocksMissed;
    this.uptime = totalBlocks > 0 ? (this.blocksProduced / totalBlocks) * 100 : 100;
  }

  /**
   * Check if validator should be jailed for missing too many blocks
   * @param {number} maxMissedBlocks - Maximum allowed missed blocks
   * @param {number} jailDuration - Jail duration in seconds
   * @returns {boolean} True if validator was jailed
   */
  checkAndJailIfNeeded(maxMissedBlocks, jailDuration) {
    if (this.blocksMissed > maxMissedBlocks) {
      this.jail(jailDuration);
      return true;
    }
    return false;
  }

  /**
   * Create a validator from JSON data
   * @param {Object} data - Validator data
   * @returns {Validator} New validator instance
   */
  static fromJSON(data) {
    const validator = new Validator(
      data.address,
      data.publicKey,
      data.stake,
      data.moniker
    );
    
    validator.state = data.state;
    validator.reputation = data.reputation;
    validator.blocksProduced = data.blocksProduced;
    validator.blocksValidated = data.blocksValidated;
    validator.blocksMissed = data.blocksMissed;
    validator.uptime = data.uptime;
    validator.lastActive = data.lastActive;
    validator.jailedUntil = data.jailedUntil;
    validator.isFirstValidator = data.isFirstValidator;
    validator.joinedDuringDistribution = data.joinedDuringDistribution;
    validator.distributionRewardClaimed = data.distributionRewardClaimed;
    
    return validator;
  }

  /**
   * Convert validator to JSON
   * @returns {Object} JSON representation of the validator
   */
  toJSON() {
    return {
      address: this.address,
      publicKey: this.publicKey,
      stake: this.stake,
      moniker: this.moniker,
      state: this.state,
      reputation: this.reputation,
      blocksProduced: this.blocksProduced,
      blocksValidated: this.blocksValidated,
      blocksMissed: this.blocksMissed,
      uptime: this.uptime,
      lastActive: this.lastActive,
      jailedUntil: this.jailedUntil,
      isFirstValidator: this.isFirstValidator,
      joinedDuringDistribution: this.joinedDuringDistribution,
      distributionRewardClaimed: this.distributionRewardClaimed
    };
  }
}

module.exports = {
  Validator,
  ValidatorState
};
