const crypto = require('crypto');

class Validator {
    constructor(blockchain, wallet) {
        this.blockchain = blockchain;
        this.wallet = wallet;
        this.stake = 0;
        this.isValidating = false;
        this.rewards = {
            firstNode: 100,  // First node gets 100 BT2C
            subsequent: 1    // Subsequent nodes get 1 BT2C
        };
    }

    setStake(amount) {
        this.stake = amount;
    }

    start() {
        if (this.stake < 1) {
            console.log('Insufficient stake to become validator. Minimum 1 BT2C required.');
            return;
        }

        this.isValidating = true;
        console.log(`Starting validator with address: ${this.wallet.getAddress()}`);
        console.log(`Initial stake: ${this.stake} BT2C`);
        this.validate();
    }

    stop() {
        this.isValidating = false;
        console.log('Validator stopped');
    }

    validate() {
        if (!this.isValidating) return;

        // Create new block with validator info
        const blockData = {
            validator: this.wallet.getAddress(),
            stake: this.stake,
            timestamp: Date.now(),
            reward: this.calculateReward()
        };

        // Sign the block data
        const dataHash = crypto.createHash('sha256')
            .update(JSON.stringify(blockData))
            .digest('hex');
        blockData.signature = this.wallet.sign(dataHash);

        const block = this.blockchain.addBlock(blockData);
        
        // Update stake with reward
        this.stake += blockData.reward;
        console.log(`Validated block ${block.index}`);
        console.log(`Reward received: ${blockData.reward} BT2C`);
        console.log(`Current stake: ${this.stake} BT2C`);

        // Schedule next validation
        setTimeout(() => this.validate(), this.blockchain.blockTime);
    }

    calculateReward() {
        const chainLength = this.blockchain.chain.length;
        if (chainLength <= 1) { // First validator after genesis
            return this.rewards.firstNode;
        }
        return this.rewards.subsequent;
    }
}

module.exports = { Validator };
