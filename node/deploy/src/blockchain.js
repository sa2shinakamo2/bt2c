const crypto = require('crypto');
const { Block } = require('./block');

class Blockchain {
    constructor() {
        this.chain = [this.createGenesisBlock()];
        this.difficulty = 4;
        this.blockTime = 1209600000; // 2 weeks in milliseconds
        this.rewards = {
            firstNode: 100,  // First node gets 100 BT2C
            subsequent: 1    // Subsequent nodes get 1 BT2C
        };
    }

    createGenesisBlock() {
        return new Block(0, Date.now(), {
            validator: null,
            reward: 0,
            data: 'Genesis Block'
        }, '0');
    }

    getLatestBlock() {
        return this.chain[this.chain.length - 1];
    }

    adjustDifficulty() {
        const latestBlock = this.getLatestBlock();
        if (latestBlock.index % 10 === 0) { // Adjust every 10 blocks
            const prevAdjustmentBlock = this.chain[this.chain.length - 10];
            const timeExpected = this.blockTime;
            const timeTaken = latestBlock.timestamp - prevAdjustmentBlock.timestamp;

            if (timeTaken < timeExpected / 2) {
                this.difficulty++;
            } else if (timeTaken > timeExpected * 2) {
                this.difficulty = Math.max(this.difficulty - 1, 1);
            }
        }
    }

    addBlock(data) {
        const previousBlock = this.getLatestBlock();
        const newBlock = new Block(
            previousBlock.index + 1,
            Date.now(),
            data,
            previousBlock.hash
        );

        newBlock.mine(this.difficulty);
        this.chain.push(newBlock);
        this.adjustDifficulty();

        return newBlock;
    }

    isValidChain(chain) {
        if (JSON.stringify(chain[0]) !== JSON.stringify(this.createGenesisBlock())) {
            return false;
        }

        for (let i = 1; i < chain.length; i++) {
            const block = chain[i];
            const previousBlock = chain[i - 1];

            if (block.previousHash !== previousBlock.hash ||
                block.hash !== block.calculateHash() ||
                !block.hasValidProof(this.difficulty)) {
                return false;
            }
        }

        return true;
    }

    replaceChain(newChain) {
        if (newChain.length <= this.chain.length) {
            console.log('Received chain is not longer than the current chain.');
            return;
        }

        if (!this.isValidChain(newChain)) {
            console.log('Received chain is invalid.');
            return;
        }

        console.log('Replacing blockchain with the new chain.');
        this.chain = newChain;
    }
}
