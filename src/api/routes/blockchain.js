/**
 * BT2C Blockchain API Routes
 * 
 * Implements the blockchain-related API endpoints including:
 * - Block retrieval by height and hash
 * - Chain information
 * - Block range retrieval
 */

const express = require('express');

/**
 * Create blockchain routes
 * @param {Object} options - Route options
 * @returns {Router} Express router
 */
function createBlockchainRoutes(options = {}) {
  const router = express.Router();
  const { blockchain, blockchainStore, pgClient } = options;
  
  /**
   * Get blockchain info
   * GET /api/v1/blockchain/info
   */
  router.get('/info', async (req, res, next) => {
    try {
      // Get blockchain info from store
      const stats = blockchainStore ? blockchainStore.getStats() : { blockCount: 0, currentHeight: 0 };
      
      res.json({
        height: stats.currentHeight,
        blockCount: stats.blockCount,
        timestamp: Date.now()
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get block by height
   * GET /api/v1/blockchain/block/:height
   */
  router.get('/block/:height', async (req, res, next) => {
    try {
      const height = parseInt(req.params.height, 10);
      
      if (isNaN(height) || height < 0) {
        return res.status(400).json({
          error: 'Invalid block height'
        });
      }
      
      // Get block from store
      const block = blockchainStore ? await blockchainStore.getBlockByHeight(height) : null;
      
      if (!block) {
        return res.status(404).json({
          error: 'Block not found'
        });
      }
      
      res.json(block);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get block by hash
   * GET /api/v1/blockchain/block/hash/:hash
   */
  router.get('/block/hash/:hash', async (req, res, next) => {
    try {
      const hash = req.params.hash;
      
      if (!hash || hash.length !== 64) {
        return res.status(400).json({
          error: 'Invalid block hash'
        });
      }
      
      // Get block from database
      if (!pgClient) {
        return res.status(503).json({
          error: 'Database not available'
        });
      }
      
      const result = await pgClient.query(
        'SELECT * FROM blocks WHERE hash = $1',
        [hash]
      );
      
      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'Block not found'
        });
      }
      
      const blockData = result.rows[0];
      
      // Get transactions for this block
      const txResult = await pgClient.query(
        'SELECT * FROM transactions WHERE block_height = $1 ORDER BY block_index ASC',
        [blockData.height]
      );
      
      // Construct full block
      const block = {
        height: blockData.height,
        hash: blockData.hash,
        previousHash: blockData.previous_hash,
        validatorAddress: blockData.validator_address,
        timestamp: blockData.timestamp,
        merkleRoot: blockData.merkle_root,
        signature: blockData.signature,
        transactions: txResult.rows.map(tx => ({
          hash: tx.hash,
          sender: tx.sender,
          recipient: tx.recipient,
          amount: parseFloat(tx.amount),
          fee: parseFloat(tx.fee),
          nonce: tx.nonce,
          timestamp: tx.timestamp,
          signature: tx.signature
        }))
      };
      
      res.json(block);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get blocks in range
   * GET /api/v1/blockchain/blocks?start=<start>&end=<end>
   */
  router.get('/blocks', async (req, res, next) => {
    try {
      const start = parseInt(req.query.start, 10) || 0;
      const end = parseInt(req.query.end, 10) || start + 10;
      
      // Limit range to 100 blocks
      if (end - start > 100) {
        return res.status(400).json({
          error: 'Range too large, maximum 100 blocks'
        });
      }
      
      if (start < 0 || end < start) {
        return res.status(400).json({
          error: 'Invalid range'
        });
      }
      
      // Get blocks from store
      const blocks = blockchainStore ? await blockchainStore.getBlocksInRange(start, end) : [];
      
      res.json({
        start,
        end,
        count: blocks.length,
        blocks
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get latest blocks
   * GET /api/v1/blockchain/latest?limit=<limit>
   */
  router.get('/latest', async (req, res, next) => {
    try {
      const limit = parseInt(req.query.limit, 10) || 10;
      
      if (limit <= 0 || limit > 100) {
        return res.status(400).json({
          error: 'Invalid limit, must be between 1 and 100'
        });
      }
      
      // Get blockchain height
      const stats = blockchainStore ? blockchainStore.getStats() : { currentHeight: 0 };
      const currentHeight = stats.currentHeight;
      
      if (currentHeight === 0) {
        return res.json({
          count: 0,
          blocks: []
        });
      }
      
      // Calculate start height
      const start = Math.max(1, currentHeight - limit + 1);
      const end = currentHeight;
      
      // Get blocks from store
      const blocks = blockchainStore ? await blockchainStore.getBlocksInRange(start, end) : [];
      
      res.json({
        count: blocks.length,
        blocks
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Validate blockchain
   * GET /api/v1/blockchain/validate?start=<start>&end=<end>
   */
  router.get('/validate', async (req, res, next) => {
    try {
      const start = parseInt(req.query.start, 10) || 1;
      const end = parseInt(req.query.end, 10) || 0;
      
      if (start < 1) {
        return res.status(400).json({
          error: 'Invalid start height'
        });
      }
      
      if (!blockchainStore) {
        return res.status(503).json({
          error: 'Blockchain store not available'
        });
      }
      
      // Validate chain
      const result = await blockchainStore.validateChain(start, end || blockchainStore.currentHeight);
      
      res.json(result);
    } catch (error) {
      next(error);
    }
  });
  
  return router;
}

module.exports = createBlockchainRoutes;
