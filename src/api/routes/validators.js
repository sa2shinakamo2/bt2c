/**
 * BT2C Validator API Routes
 * 
 * Implements the validator-related API endpoints including:
 * - Validator status and list
 * - Validator performance metrics
 * - Staking and unstaking operations
 * - Jailing and unjailing
 */

const express = require('express');

/**
 * Create validator routes
 * @param {Object} options - Route options
 * @returns {Router} Express router
 */
function createValidatorRoutes(options = {}) {
  const router = express.Router();
  const { consensusEngine, stateMachine, pgClient } = options;
  
  /**
   * Get validator list
   * GET /api/v1/validators/list
   */
  router.get('/list', async (req, res, next) => {
    try {
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Get validators from state machine
      const validators = await stateMachine.getValidators();
      
      res.json({
        count: validators.length,
        validators
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get validator status
   * GET /api/v1/validators/status/:address
   */
  router.get('/status/:address', async (req, res, next) => {
    try {
      const address = req.params.address;
      
      if (!address) {
        return res.status(400).json({
          error: 'Invalid validator address'
        });
      }
      
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Get validator from state machine
      const validator = await stateMachine.getValidator(address);
      
      if (!validator) {
        return res.status(404).json({
          error: 'Validator not found'
        });
      }
      
      // Get performance metrics
      let performance = null;
      
      if (pgClient) {
        // Get blocks produced in last 24 hours
        const blocksResult = await pgClient.query(
          'SELECT COUNT(*) as block_count FROM blocks WHERE validator_address = $1 AND timestamp > NOW() - INTERVAL \'24 hours\'',
          [address]
        );
        
        // Get missed blocks in last 24 hours
        const missedResult = await pgClient.query(
          'SELECT COUNT(*) as missed_count FROM missed_blocks WHERE validator_address = $1 AND timestamp > NOW() - INTERVAL \'24 hours\'',
          [address]
        );
        
        performance = {
          last24Hours: {
            blocksProduced: parseInt(blocksResult.rows[0].block_count, 10),
            blocksMissed: parseInt(missedResult.rows[0].missed_count, 10)
          }
        };
      }
      
      res.json({
        ...validator,
        performance
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get validator performance
   * GET /api/v1/validators/performance/:address
   */
  router.get('/performance/:address', async (req, res, next) => {
    try {
      const address = req.params.address;
      const days = parseInt(req.query.days, 10) || 7;
      
      if (!address) {
        return res.status(400).json({
          error: 'Invalid validator address'
        });
      }
      
      if (days <= 0 || days > 30) {
        return res.status(400).json({
          error: 'Invalid days parameter, must be between 1 and 30'
        });
      }
      
      if (!pgClient) {
        return res.status(503).json({
          error: 'Database not available'
        });
      }
      
      // Check if validator exists
      const validatorResult = await pgClient.query(
        'SELECT * FROM validators WHERE address = $1',
        [address]
      );
      
      if (validatorResult.rows.length === 0) {
        return res.status(404).json({
          error: 'Validator not found'
        });
      }
      
      // Get daily performance
      const dailyResult = await pgClient.query(
        `SELECT 
          DATE(timestamp) as day,
          COUNT(*) as blocks_produced
        FROM blocks 
        WHERE validator_address = $1 
          AND timestamp > NOW() - INTERVAL '$2 days'
        GROUP BY DATE(timestamp)
        ORDER BY day ASC`,
        [address, days]
      );
      
      // Get missed blocks
      const missedResult = await pgClient.query(
        `SELECT 
          DATE(timestamp) as day,
          COUNT(*) as blocks_missed
        FROM missed_blocks 
        WHERE validator_address = $1 
          AND timestamp > NOW() - INTERVAL '$2 days'
        GROUP BY DATE(timestamp)
        ORDER BY day ASC`,
        [address, days]
      );
      
      // Get jailing events
      const jailingResult = await pgClient.query(
        `SELECT 
          timestamp,
          reason
        FROM validator_events 
        WHERE validator_address = $1 
          AND event_type = 'jailed'
          AND timestamp > NOW() - INTERVAL '$2 days'
        ORDER BY timestamp ASC`,
        [address, days]
      );
      
      // Get unjailing events
      const unjailingResult = await pgClient.query(
        `SELECT 
          timestamp
        FROM validator_events 
        WHERE validator_address = $1 
          AND event_type = 'unjailed'
          AND timestamp > NOW() - INTERVAL '$2 days'
        ORDER BY timestamp ASC`,
        [address, days]
      );
      
      // Calculate uptime percentage
      let totalBlocks = 0;
      let missedBlocks = 0;
      
      dailyResult.rows.forEach(row => {
        totalBlocks += parseInt(row.blocks_produced, 10);
      });
      
      missedResult.rows.forEach(row => {
        missedBlocks += parseInt(row.blocks_missed, 10);
      });
      
      const uptime = totalBlocks + missedBlocks > 0 
        ? ((totalBlocks / (totalBlocks + missedBlocks)) * 100).toFixed(2)
        : 100;
      
      // Format daily data
      const dailyData = [];
      
      // Create a map of days to blocks produced
      const blocksMap = {};
      dailyResult.rows.forEach(row => {
        blocksMap[row.day] = parseInt(row.blocks_produced, 10);
      });
      
      // Create a map of days to blocks missed
      const missedMap = {};
      missedResult.rows.forEach(row => {
        missedMap[row.day] = parseInt(row.blocks_missed, 10);
      });
      
      // Generate daily data for the past 'days' days
      for (let i = 0; i < days; i++) {
        const date = new Date();
        date.setDate(date.getDate() - (days - i - 1));
        const day = date.toISOString().split('T')[0];
        
        dailyData.push({
          day,
          blocksProduced: blocksMap[day] || 0,
          blocksMissed: missedMap[day] || 0,
          uptime: blocksMap[day] + (missedMap[day] || 0) > 0
            ? ((blocksMap[day] || 0) / (blocksMap[day] + (missedMap[day] || 0)) * 100).toFixed(2)
            : 100
        });
      }
      
      res.json({
        address,
        days,
        uptime,
        totalBlocksProduced: totalBlocks,
        totalBlocksMissed: missedBlocks,
        jailingEvents: jailingResult.rows.map(event => ({
          timestamp: event.timestamp,
          reason: event.reason
        })),
        unjailingEvents: unjailingResult.rows.map(event => ({
          timestamp: event.timestamp
        })),
        dailyData
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Register as validator
   * POST /api/v1/validators/register
   */
  router.post('/register', async (req, res, next) => {
    try {
      const { address, publicKey, stake, signature } = req.body;
      
      // Validate request
      if (!address || !publicKey || !stake || !signature) {
        return res.status(400).json({
          error: 'Invalid request',
          required: ['address', 'publicKey', 'stake', 'signature']
        });
      }
      
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Register validator
      const result = await stateMachine.registerValidator({
        address,
        publicKey,
        stake,
        signature
      });
      
      if (!result.success) {
        return res.status(400).json({
          error: result.error
        });
      }
      
      res.status(201).json({
        status: 'success',
        address,
        timestamp: Date.now()
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Stake tokens
   * POST /api/v1/validators/stake
   */
  router.post('/stake', async (req, res, next) => {
    try {
      const { address, amount, signature } = req.body;
      
      // Validate request
      if (!address || !amount || !signature) {
        return res.status(400).json({
          error: 'Invalid request',
          required: ['address', 'amount', 'signature']
        });
      }
      
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Stake tokens
      const result = await stateMachine.stakeTokens({
        address,
        amount,
        signature
      });
      
      if (!result.success) {
        return res.status(400).json({
          error: result.error
        });
      }
      
      res.json({
        status: 'success',
        address,
        amount,
        timestamp: Date.now()
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Unstake tokens
   * POST /api/v1/validators/unstake
   */
  router.post('/unstake', async (req, res, next) => {
    try {
      const { address, amount, signature } = req.body;
      
      // Validate request
      if (!address || !amount || !signature) {
        return res.status(400).json({
          error: 'Invalid request',
          required: ['address', 'amount', 'signature']
        });
      }
      
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Unstake tokens
      const result = await stateMachine.unstakeTokens({
        address,
        amount,
        signature
      });
      
      if (!result.success) {
        return res.status(400).json({
          error: result.error
        });
      }
      
      res.json({
        status: 'success',
        address,
        amount,
        timestamp: Date.now()
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Unjail validator
   * POST /api/v1/validators/unjail
   */
  router.post('/unjail', async (req, res, next) => {
    try {
      const { address, signature } = req.body;
      
      // Validate request
      if (!address || !signature) {
        return res.status(400).json({
          error: 'Invalid request',
          required: ['address', 'signature']
        });
      }
      
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Unjail validator
      const result = await stateMachine.unjailValidator({
        address,
        signature
      });
      
      if (!result.success) {
        return res.status(400).json({
          error: result.error
        });
      }
      
      res.json({
        status: 'success',
        address,
        timestamp: Date.now()
      });
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get initial distribution status
   * GET /api/v1/validators/distribution
   */
  router.get('/distribution', async (req, res, next) => {
    try {
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      // Get distribution status
      const status = await stateMachine.getDistributionStatus();
      
      res.json(status);
    } catch (error) {
      next(error);
    }
  });
  
  return router;
}

module.exports = createValidatorRoutes;
