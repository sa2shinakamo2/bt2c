const { Blockchain } = require('./blockchain');
const { Validator } = require('./validator');
const { Wallet } = require('./wallet');
const express = require('express');
const cors = require('cors');

class Node {
    constructor(wallet) {
        this.blockchain = new Blockchain();
        this.wallet = wallet;
        this.validator = new Validator(this.blockchain, this.wallet);
        this.app = express();
        this.setupAPI();
    }

    setupAPI() {
        this.app.use(cors());
        this.app.use(express.json());

        // Get node info
        this.app.get('/info', (req, res) => {
            res.json({
                address: this.wallet.getAddress(),
                isValidator: this.validator.isValidating,
                stake: this.validator.stake,
                blockHeight: this.blockchain.chain.length
            });
        });

        // Get blockchain
        this.app.get('/blocks', (req, res) => {
            res.json(this.blockchain.chain);
        });

        // Get balance
        this.app.get('/balance/:address', (req, res) => {
            let balance = 0;
            const address = req.params.address;

            for (const block of this.blockchain.chain) {
                if (block.data.validator === address) {
                    balance += block.data.reward || 0;
                }
            }

            res.json({ address, balance });
        });

        // Get validators
        this.app.get('/validators', (req, res) => {
            const validators = new Set();
            for (const block of this.blockchain.chain) {
                if (block.data.validator) {
                    validators.add(block.data.validator);
                }
            }
            res.json(Array.from(validators));
        });
    }

    start(port = 3000) {
        // Start validator
        this.validator.setStake(1);
        this.validator.start();

        // Start API server
        this.app.listen(port, () => {
            console.log(`Node API running on http://localhost:${port}`);
            console.log('Available endpoints:');
            console.log('  GET /info - Node information');
            console.log('  GET /blocks - Blockchain data');
            console.log('  GET /balance/:address - Get balance for address');
            console.log('  GET /validators - List of validators');
        });
    }
}

// Load wallet and start node
console.log('Enter your wallet password to start the node:');
const prompt = require('prompt-sync')();
const password = prompt('Password: ');

const wallet = Wallet.load(password);
if (wallet) {
    const node = new Node(wallet);
    node.start();
} else {
    console.error('Failed to load wallet. Make sure you have created one using:');
    console.error('./cli.js create-wallet');
}
