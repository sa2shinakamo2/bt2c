// Distribution period functionality
document.addEventListener('DOMContentLoaded', async function() {
    const API_URL = 'http://localhost:8000/api';
    
    // Get distribution period end time
    async function getDistributionPeriodEnd() {
        try {
            const response = await fetch(`${API_URL}/distribution/info`);
            const data = await response.json();
            return new Date(data.end_time * 1000);
        } catch (error) {
            console.error('Error fetching distribution period:', error);
            return null;
        }
    }

    // Check if address is eligible for distribution
    async function checkEligibility(address) {
        try {
            const response = await fetch(`${API_URL}/distribution/check/${address}`);
            const data = await response.json();
            return {
                eligible: data.eligible,
                type: data.node_type,
                message: data.message
            };
        } catch (error) {
            console.error('Error checking eligibility:', error);
            return null;
        }
    }

    // Update distribution end time display
    async function updateDistributionTimer() {
        const endTime = await getDistributionPeriodEnd();
        if (!endTime) return;

        const timerElement = document.getElementById('distribution-end');
        if (!timerElement) return;

        function updateDisplay() {
            const now = new Date();
            const timeLeft = endTime - now;

            if (timeLeft <= 0) {
                timerElement.textContent = 'Distribution period has ended';
                return;
            }

            const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));

            timerElement.textContent = `${days}d ${hours}h ${minutes}m remaining`;
        }

        updateDisplay();
        setInterval(updateDisplay, 60000); // Update every minute
    }

    // Handle eligibility check button
    const checkButton = document.getElementById('check-eligibility');
    if (checkButton) {
        checkButton.addEventListener('click', async () => {
            const address = prompt('Enter your BT2C address:');
            if (!address) return;

            const result = await checkEligibility(address);
            if (!result) {
                alert('Error checking eligibility. Please try again.');
                return;
            }

            let message = '';
            if (result.eligible) {
                if (result.type === 'developer') {
                    message = 'Congratulations! You are eligible for the 100 BT2C developer reward as the first node!';
                } else {
                    message = 'Congratulations! You are eligible to receive 1 BT2C during the distribution period.';
                }
            } else {
                message = result.message || 'Sorry, you are not eligible for the distribution period.';
            }

            // Show result in a modal or alert
            alert(message);
        });
    }

    // Initialize
    updateDistributionTimer();
});
