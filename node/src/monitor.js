const axios = require('axios');
const nodemailer = require('nodemailer');

class NodeMonitor {
    constructor(nodeUrl, emailConfig) {
        this.nodeUrl = nodeUrl;
        this.emailConfig = emailConfig;
        this.lastBlockHeight = 0;
        this.lastCheckTime = Date.now();
    }

    async checkNodeHealth() {
        try {
            // Check node info
            const info = await axios.get(`${this.nodeUrl}/info`);
            const currentHeight = info.data.blockHeight;
            const currentTime = Date.now();

            // Check if node is validating
            if (!info.data.isValidator) {
                await this.sendAlert('Node is not validating');
                return false;
            }

            // Check if blocks are being produced
            if (currentHeight === this.lastBlockHeight && 
                (currentTime - this.lastCheckTime) > 1209600000) { // 2 weeks
                await this.sendAlert('No new blocks produced in the last distribution period');
                return false;
            }

            // Update state
            this.lastBlockHeight = currentHeight;
            this.lastCheckTime = currentTime;
            return true;

        } catch (error) {
            await this.sendAlert(`Node error: ${error.message}`);
            return false;
        }
    }

    async sendAlert(message) {
        if (!this.emailConfig) return;

        const transporter = nodemailer.createTransport(this.emailConfig);
        await transporter.sendMail({
            from: this.emailConfig.auth.user,
            to: this.emailConfig.alertEmail,
            subject: 'BT2C Node Alert',
            text: message
        });
    }

    async start(checkInterval = 300000) { // Check every 5 minutes
        console.log('Starting node monitor...');
        setInterval(async () => {
            const healthy = await this.checkNodeHealth();
            console.log(`Node health check: ${healthy ? 'OK' : 'FAILED'}`);
        }, checkInterval);
    }
}

// Example usage:
/*
const monitor = new NodeMonitor('http://your-node-ip:3000', {
    host: 'smtp.gmail.com',
    port: 587,
    secure: false,
    auth: {
        user: 'your-email@gmail.com',
        pass: 'your-app-specific-password'
    },
    alertEmail: 'your-alert-email@example.com'
});

monitor.start();
*/

module.exports = { NodeMonitor };
