/**
 * BT2C Account API Routes
 * 
 * Implements the account-related API endpoints including:
 * - Account balance and details
 * - Account transaction history
 * - Account nonce information
 */

const express = require('express');

/**
 * Create account routes
 * @param {Object} options - Route options
 * @returns {Router} Express router
 */
function createAccountRoutes(options = {}) {
  const router = express.Router();
  const { stateMachine, pgClient } = options;
  
  /**
   * Get account balance and details
   * GET /api/v1/accounts/:address
   */
  router.get('/:address', async (req, res, next) => {
    try {
      const address = req.params.address;
      
      if (!address) {
        return res.status(400).json({
          error: 'Invalid account address'
        });
      }
      
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Get account from state machine
      const account = await stateMachine.getAccount(address);
      
      if (!account) {
        return res.status(404).json({
          error: 'Account not found'
        });
      }
      
      // Get transaction count
      let transactionCount = 0;
      
      if (pgClient) {
        const result = await pgClient.query(
          'SELECT COUNT(*) as count FROM transactions WHERE sender = $1 OR recipient = $1',
          [address]
        );
        
        transactionCount = parseInt(result.rows[0].count, 10);
      }
      
      res.json({
        address: account.address,
        balance: account.balance,
        nonce: account.nonce,
        transactionCount,
        isValidator: account.isValidator || false,
        stake: account.stake || 0,
        lastActive: account.lastActive || null
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get account nonce
   * GET /api/v1/accounts/:address/nonce
   */
  router.get('/:address/nonce', async (req, res, next) => {
    try {
      const address = req.params.address;
      
      if (!address) {
        return res.status(400).json({
          error: 'Invalid account address'
        });
      }
      
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Get account from state machine
      const account = await stateMachine.getAccount(address);
      
      if (!account) {
        return res.status(404).json({
          error: 'Account not found'
        });
      }
      
      res.json({
        address: account.address,
        nonce: account.nonce
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get account transaction history
   * GET /api/v1/accounts/:address/transactions
   */
  router.get('/:address/transactions', async (req, res, next) => {
    try {
      const address = req.params.address;
      const limit = parseInt(req.query.limit, 10) || 20;
      const offset = parseInt(req.query.offset, 10) || 0;
      
      if (!address) {
        return res.status(400).json({
          error: 'Invalid account address'
        });
      }
      
      if (limit <= 0 || limit > 100) {
        return res.status(400).json({
          error: 'Invalid limit, must be between 1 and 100'
        });
      }
      
      if (offset < 0) {
        return res.status(400).json({
          error: 'Invalid offset'
        });
      }
      
      if (!pgClient) {
        return res.status(503).json({
          error: 'Database not available'
        });
      }
      
      // Get transactions from database
      const result = await pgClient.query(
        'SELECT t.*, b.height as block_height FROM transactions t JOIN blocks b ON t.block_height = b.height WHERE t.sender = $1 OR t.recipient = $1 ORDER BY b.height DESC, t.block_index DESC LIMIT $2 OFFSET $3',
        [address, limit, offset]
      );
      
      // Get current blockchain height for confirmations
      const heightResult = await pgClient.query('SELECT MAX(height) as current_height FROM blocks');
      const currentHeight = heightResult.rows[0].current_height || 0;
      
      // Format transactions
      const transactions = result.rows.map(tx => {
        const confirmations = currentHeight - tx.block_height + 1;
        
        return {
          hash: tx.hash,
          sender: tx.sender,
          recipient: tx.recipient,
          amount: parseFloat(tx.amount),
          fee: parseFloat(tx.fee),
          nonce: tx.nonce,
          timestamp: tx.timestamp,
          signature: tx.signature,
          blockHeight: tx.block_height,
          blockIndex: tx.block_index,
          status: 'confirmed',
          confirmations,
          // Add direction relative to the requested address
          direction: tx.sender === address ? 'outgoing' : 'incoming'
        };
      });
      
      // Get total count
      const countResult = await pgClient.query(
        'SELECT COUNT(*) as total FROM transactions t WHERE t.sender = $1 OR t.recipient = $1',
        [address]
      );
      
      const total = parseInt(countResult.rows[0].total, 10);
      
      res.json({
        address,
        count: transactions.length,
        total,
        transactions
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get account rewards history
   * GET /api/v1/accounts/:address/rewards
   */
  router.get('/:address/rewards', async (req, res, next) => {
    try {
      const address = req.params.address;
      const limit = parseInt(req.query.limit, 10) || 20;
      const offset = parseInt(req.query.offset, 10) || 0;
      
      if (!address) {
        return res.status(400).json({
          error: 'Invalid account address'
        });
      }
      
      if (limit <= 0 || limit > 100) {
        return res.status(400).json({
          error: 'Invalid limit, must be between 1 and 100'
        });
      }
      
      if (offset < 0) {
        return res.status(400).json({
          error: 'Invalid offset'
        });
      }
      
      if (!pgClient) {
        return res.status(503).json({
          error: 'Database not available'
        });
      }
      
      // Get rewards from database
      const result = await pgClient.query(
        'SELECT * FROM rewards WHERE validator_address = $1 ORDER BY block_height DESC LIMIT $2 OFFSET $3',
        [address, limit, offset]
      );
      
      // Format rewards
      const rewards = result.rows.map(reward => ({
        blockHeight: reward.block_height,
        amount: parseFloat(reward.amount),
        timestamp: reward.timestamp,
        type: reward.type
      }));
      
      // Get total count
      const countResult = await pgClient.query(
        'SELECT COUNT(*) as total FROM rewards WHERE validator_address = $1',
        [address]
      );
      
      const total = parseInt(countResult.rows[0].total, 10);
      
      res.json({
        address,
        count: rewards.length,
        total,
        rewards
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get richlist (top accounts by balance)
   * GET /api/v1/accounts/richlist
   */
  router.get('/richlist', async (req, res, next) => {
    try {
      const limit = parseInt(req.query.limit, 10) || 100;
      
      if (limit <= 0 || limit > 1000) {
        return res.status(400).json({
          error: 'Invalid limit, must be between 1 and 1000'
        });
      }
      
      if (!pgClient) {
        return res.status(503).json({
          error: 'Database not available'
        });
      }
      
      // Get top accounts by balance
      const result = await pgClient.query(
        'SELECT address, balance FROM accounts ORDER BY balance DESC LIMIT $1',
        [limit]
      );
      
      // Format accounts
      const accounts = result.rows.map(account => ({
        address: account.address,
        balance: parseFloat(account.balance)
      }));
      
      // Get total supply
      const supplyResult = await pgClient.query('SELECT SUM(balance) as total_supply FROM accounts');
      const totalSupply = parseFloat(supplyResult.rows[0].total_supply) || 0;
      
      res.json({
        count: accounts.length,
        totalSupply,
        accounts
      });
    } catch (error) {
      next(error);
    }
  });
  
  return router;
}

module.exports = createAccountRoutes;
