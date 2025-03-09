const express = require('express');
const WebSocket = require('ws');
const { Blockchain } = require('./blockchain');
const { Validator } = require('./validator');
const { P2PServer } = require('./p2p');

const HTTP_PORT = process.env.HTTP_PORT || 3001;
const P2P_PORT = process.env.P2P_PORT || 6001;

class Node {
    constructor() {
        this.blockchain = new Blockchain();
        this.validator = new Validator(this.blockchain);
        this.p2pServer = new P2PServer(this.blockchain);
        this.app = express();
        this.setupAPI();
    }

    setupAPI() {
        this.app.use(express.json());

        // Get blockchain
        this.app.get('/blocks', (req, res) => {
            res.json(this.blockchain.chain);
        });

        // Add block
        this.app.post('/mine', (req, res) => {
            const block = this.blockchain.addBlock(req.body.data);
            this.p2pServer.syncChains();
            res.json(block);
        });

        // Get peers
        this.app.get('/peers', (req, res) => {
            res.json(this.p2pServer.getPeers());
        });
    }

    start() {
        // Start HTTP server
        this.app.listen(HTTP_PORT, () => {
            console.log(`HTTP server listening on port ${HTTP_PORT}`);
        });

        // Start P2P server
        this.p2pServer.listen(P2P_PORT);

        // Start validator
        this.validator.start();
    }
}

const node = new Node();
node.start();
