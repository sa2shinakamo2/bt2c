/**
 * BT2C Transaction API Routes
 * 
 * Implements the transaction-related API endpoints including:
 * - Transaction submission
 * - Transaction status and details
 * - Mempool transaction listing
 */

const express = require('express');

/**
 * Create transaction routes
 * @param {Object} options - Route options
 * @returns {Router} Express router
 */
function createTransactionRoutes(options = {}) {
  const router = express.Router();
  const { transactionPool, stateMachine, pgClient } = options;
  
  /**
   * Submit transaction
   * POST /api/v1/transactions/submit
   */
  router.post('/submit', async (req, res, next) => {
    try {
      const transaction = req.body;
      
      // Validate transaction structure
      if (!transaction || !transaction.sender || !transaction.recipient || 
          !transaction.amount || !transaction.fee || !transaction.nonce || 
          !transaction.signature) {
        return res.status(400).json({
          error: 'Invalid transaction format',
          required: ['sender', 'recipient', 'amount', 'fee', 'nonce', 'signature']
        });
      }
      
      if (!transactionPool) {
        return res.status(503).json({
          error: 'Transaction pool not available'
        });
      }
      
      // Add transaction to pool
      const result = transactionPool.addTransaction(transaction);
      
      if (!result.valid) {
        return res.status(400).json({
          error: result.error,
          details: result.details
        });
      }
      
      res.status(201).json({
        status: 'success',
        hash: transaction.hash,
        timestamp: Date.now()
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get transaction by hash
   * GET /api/v1/transactions/:hash
   */
  router.get('/:hash', async (req, res, next) => {
    try {
      const hash = req.params.hash;
      
      if (!hash || hash.length !== 64) {
        return res.status(400).json({
          error: 'Invalid transaction hash'
        });
      }
      
      // Check mempool first
      if (transactionPool) {
        const mempoolTx = transactionPool.getTransaction(hash);
        
        if (mempoolTx) {
          return res.json({
            ...mempoolTx,
            status: 'pending',
            confirmations: 0
          });
        }
      }
      
      // Check database
      if (!pgClient) {
        return res.status(503).json({
          error: 'Database not available'
        });
      }
      
      const result = await pgClient.query(
        'SELECT t.*, b.height as block_height FROM transactions t JOIN blocks b ON t.block_height = b.height WHERE t.hash = $1',
        [hash]
      );
      
      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'Transaction not found'
        });
      }
      
      const tx = result.rows[0];
      
      // Get current blockchain height for confirmations
      const heightResult = await pgClient.query('SELECT MAX(height) as current_height FROM blocks');
      const currentHeight = heightResult.rows[0].current_height || 0;
      const confirmations = currentHeight - tx.block_height + 1;
      
      res.json({
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
        confirmations
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get mempool transactions
   * GET /api/v1/transactions/mempool/list
   */
  router.get('/mempool/list', async (req, res, next) => {
    try {
      if (!transactionPool) {
        return res.status(503).json({
          error: 'Transaction pool not available'
        });
      }
      
      const limit = parseInt(req.query.limit, 10) || 100;
      const offset = parseInt(req.query.offset, 10) || 0;
      
      if (limit <= 0 || limit > 1000) {
        return res.status(400).json({
          error: 'Invalid limit, must be between 1 and 1000'
        });
      }
      
      if (offset < 0) {
        return res.status(400).json({
          error: 'Invalid offset'
        });
      }
      
      // Get transactions from pool
      const transactions = transactionPool.getTransactions(limit, offset);
      
      res.json({
        count: transactions.length,
        total: transactionPool.getTransactionCount(),
        transactions
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get mempool stats
   * GET /api/v1/transactions/mempool/stats
   */
  router.get('/mempool/stats', async (req, res, next) => {
    try {
      if (!transactionPool) {
        return res.status(503).json({
          error: 'Transaction pool not available'
        });
      }
      
      const stats = transactionPool.getStats();
      
      res.json(stats);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get transactions by address
   * GET /api/v1/transactions/address/:address
   */
  router.get('/address/:address', async (req, res, next) => {
    try {
      const address = req.params.address;
      const limit = parseInt(req.query.limit, 10) || 20;
      const offset = parseInt(req.query.offset, 10) || 0;
      
      if (!address) {
        return res.status(400).json({
          error: 'Invalid address'
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
      
      // Check database
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
          confirmations
        };
      });
      
      // Get pending transactions from mempool
      let pendingTransactions = [];
      
      if (transactionPool) {
        pendingTransactions = transactionPool.getTransactionsByAddress(address);
        
        // Format pending transactions
        pendingTransactions = pendingTransactions.map(tx => ({
          ...tx,
          status: 'pending',
          confirmations: 0
        }));
      }
      
      // Combine and sort by timestamp (newest first)
      const allTransactions = [...pendingTransactions, ...transactions]
        .sort((a, b) => b.timestamp - a.timestamp)
        .slice(0, limit);
      
      // Get total count
      const countResult = await pgClient.query(
        'SELECT COUNT(*) as total FROM transactions t WHERE t.sender = $1 OR t.recipient = $1',
        [address]
      );
      
      const total = parseInt(countResult.rows[0].total, 10) + pendingTransactions.length;
      
      res.json({
        address,
        count: allTransactions.length,
        total,
        transactions: allTransactions
      });
    } catch (error) {
      next(error);
    }
  });
  
  return router;
}

module.exports = createTransactionRoutes;
