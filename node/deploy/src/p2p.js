const WebSocket = require('ws');

class P2PServer {
    constructor(blockchain) {
        this.blockchain = blockchain;
        this.sockets = [];
    }

    listen(port) {
        const server = new WebSocket.Server({ port });
        server.on('connection', socket => this.connectSocket(socket));
        console.log(`P2P server listening on port ${port}`);
    }

    connectSocket(socket) {
        this.sockets.push(socket);
        console.log('Socket connected');
        this.messageHandler(socket);
        this.sendChain(socket);
    }

    messageHandler(socket) {
        socket.on('message', message => {
            const data = JSON.parse(message);
            this.blockchain.replaceChain(data);
        });
    }

    sendChain(socket) {
        socket.send(JSON.stringify(this.blockchain.chain));
    }

    syncChains() {
        this.sockets.forEach(socket => this.sendChain(socket));
    }

    getPeers() {
        return this.sockets.map(socket => socket._socket.remoteAddress);
    }
}

module.exports = { P2PServer };
