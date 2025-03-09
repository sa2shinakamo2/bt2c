module.exports = {
    // Node configuration
    port: process.env.PORT || 3000,
    host: process.env.HOST || '0.0.0.0',

    // Blockchain configuration
    blockTime: 1209600000, // 2 weeks in milliseconds
    minStake: 1,
    firstNodeReward: 100,
    subsequentReward: 1,

    // Security
    corsOrigins: [
        'https://bt2c.net',
        'http://localhost:3000'
    ],

    // Monitoring
    healthCheckInterval: 300000, // 5 minutes

    // P2P Network
    p2pPort: process.env.P2P_PORT || 6001,
    initialPeers: [
        // Add known peers here
    ]
};
