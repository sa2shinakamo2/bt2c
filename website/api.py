from flask import Flask, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Mock data for testing
DISTRIBUTION_BLOCKS = 2016  # About 2 weeks worth of blocks
CURRENT_BLOCK = 100  # Mock current block number
COINS_PER_BLOCK = 100

@app.route('/api/distribution/info')
def get_distribution_info():
    """Get information about the current distribution period."""
    current_time = int(time.time())
    end_time = current_time + (DISTRIBUTION_BLOCKS - CURRENT_BLOCK) * 600  # 10 minutes per block
    
    response = jsonify({
        'in_distribution': CURRENT_BLOCK < DISTRIBUTION_BLOCKS,
        'blocks_remaining': DISTRIBUTION_BLOCKS - CURRENT_BLOCK,
        'coins_per_block': COINS_PER_BLOCK,
        'end_time': end_time
    })
    return response

@app.route('/api/distribution/check/<address>')
def check_eligibility(address):
    """Check if an address is eligible for distribution."""
    try:
        is_valid = len(address) == 64  # Simple validation for now
        response = jsonify({
            'eligible': is_valid and CURRENT_BLOCK < DISTRIBUTION_BLOCKS,
            'node_type': 'validator' if is_valid else None,
            'message': 'Address is eligible for distribution' if is_valid else 'Invalid address'
        })
        return response
    except Exception as e:
        return jsonify({
            'eligible': False,
            'node_type': None,
            'message': str(e)
        }), 400

if __name__ == '__main__':
    print("Starting API server on http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=True)
