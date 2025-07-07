/**
 * BT2C Stats API Routes
 * 
 * Implements the statistics-related API endpoints including:
 * - Network statistics
 * - Blockchain statistics
 * - Validator statistics
 * - Transaction statistics
 */

const express = require('express');

/**
 * Create stats routes
 * @param {Object} options - Route options
 * @returns {Router} Express router
 */
function createStatsRoutes(options = {}) {
  const router = express.Router();
  const { blockchain, stateMachine, transactionPool, consensusEngine, pgClient, redisClient } = options;
  
  /**
   * Get network overview statistics
   * GET /api/v1/stats/overview
   */
  router.get('/overview', async (req, res, next) => {
    try {
      // Initialize stats object
      const stats = {
        timestamp: Date.now(),
        blockchain: {
          height: 0,
          blockCount: 0,
          lastBlockTime: null
        },
        transactions: {
          total: 0,
          pending: 0,
          last24Hours: 0
        },
        validators: {
          total: 0,
          active: 0,
          jailed: 0
        },
        supply: {
          total: 0,
          circulating: 0,
          staked: 0
        },
        distribution: {
          isActive: false,
          endTime: null,
          validatorsRewarded: 0
        }
      };
      
      // Get blockchain stats
      if (blockchain) {
        const blockchainStats = blockchain.getStats();
        stats.blockchain.height = blockchainStats.currentHeight;
        stats.blockchain.blockCount = blockchainStats.blockCount;
        stats.blockchain.lastBlockTime = blockchainStats.lastBlockTime;
      }
      
      // Get transaction stats
      if (transactionPool) {
        const poolStats = transactionPool.getStats();
        stats.transactions.pending = poolStats.count;
      }
      
      // Get database stats
      if (pgClient) {
        // Total transactions
        const txResult = await pgClient.query('SELECT COUNT(*) as count FROM transactions');
        stats.transactions.total = parseInt(txResult.rows[0].count, 10);
        
        // Transactions in last 24 hours
        const tx24Result = await pgClient.query(
          'SELECT COUNT(*) as count FROM transactions WHERE timestamp > NOW() - INTERVAL \'24 hours\''
        );
        stats.transactions.last24Hours = parseInt(tx24Result.rows[0].count, 10);
        
        // Validator counts
        const validatorResult = await pgClient.query(
          'SELECT status, COUNT(*) as count FROM validators GROUP BY status'
        );
        
        validatorResult.rows.forEach(row => {
          stats.validators.total += parseInt(row.count, 10);
          
          if (row.status === 'active') {
            stats.validators.active = parseInt(row.count, 10);
          } else if (row.status === 'jailed') {
            stats.validators.jailed = parseInt(row.count, 10);
          }
        });
        
        // Supply stats
        const supplyResult = await pgClient.query('SELECT SUM(balance) as total FROM accounts');
        stats.supply.total = parseFloat(supplyResult.rows[0].total) || 0;
        
        const circulatingResult = await pgClient.query(
          'SELECT SUM(balance) as circulating FROM accounts WHERE address NOT IN (SELECT address FROM system_accounts)'
        );
        stats.supply.circulating = parseFloat(circulatingResult.rows[0].circulating) || 0;
        
        const stakedResult = await pgClient.query('SELECT SUM(stake) as staked FROM validators');
        stats.supply.staked = parseFloat(stakedResult.rows[0].staked) || 0;
      }
      
      // Get distribution status
      if (stateMachine) {
        const distributionStatus = await stateMachine.getDistributionStatus();
        stats.distribution = distributionStatus;
      }
      
      res.json(stats);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get blockchain statistics
   * GET /api/v1/stats/blockchain
   */
  router.get('/blockchain', async (req, res, next) => {
    try {
      // Initialize stats object
      const stats = {
        timestamp: Date.now(),
        height: 0,
        blockCount: 0,
        lastBlockTime: null,
        blockTimes: [],
        blocksPerDay: [],
        transactionsPerBlock: []
      };
      
      // Get blockchain stats
      if (blockchain) {
        const blockchainStats = blockchain.getStats();
        stats.height = blockchainStats.currentHeight;
        stats.blockCount = blockchainStats.blockCount;
        stats.lastBlockTime = blockchainStats.lastBlockTime;
      }
      
      // Get database stats
      if (pgClient) {
        // Average block time for last 100 blocks
        const blockTimeResult = await pgClient.query(
          `SELECT 
            height,
            timestamp,
            EXTRACT(EPOCH FROM (timestamp - lag(timestamp) OVER (ORDER BY height))) as block_time
          FROM blocks
          ORDER BY height DESC
          LIMIT 100`
        );
        
        stats.blockTimes = blockTimeResult.rows
          .filter(row => row.block_time !== null)
          .map(row => ({
            height: row.height,
            timestamp: row.timestamp,
            blockTime: parseFloat(row.block_time)
          }));
        
        // Blocks per day for last 30 days
        const blocksPerDayResult = await pgClient.query(
          `SELECT 
            DATE(timestamp) as day,
            COUNT(*) as block_count
          FROM blocks
          WHERE timestamp > NOW() - INTERVAL '30 days'
          GROUP BY DATE(timestamp)
          ORDER BY day ASC`
        );
        
        stats.blocksPerDay = blocksPerDayResult.rows.map(row => ({
          day: row.day,
          count: parseInt(row.block_count, 10)
        }));
        
        // Transactions per block for last 100 blocks
        const txPerBlockResult = await pgClient.query(
          `SELECT 
            b.height,
            b.timestamp,
            COUNT(t.hash) as tx_count
          FROM blocks b
          LEFT JOIN transactions t ON b.height = t.block_height
          GROUP BY b.height, b.timestamp
          ORDER BY b.height DESC
          LIMIT 100`
        );
        
        stats.transactionsPerBlock = txPerBlockResult.rows.map(row => ({
          height: row.height,
          timestamp: row.timestamp,
          count: parseInt(row.tx_count, 10)
        }));
      }
      
      res.json(stats);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get transaction statistics
   * GET /api/v1/stats/transactions
   */
  router.get('/transactions', async (req, res, next) => {
    try {
      // Initialize stats object
      const stats = {
        timestamp: Date.now(),
        total: 0,
        pending: 0,
        last24Hours: 0,
        transactionsPerDay: [],
        feeStats: {
          average: 0,
          min: 0,
          max: 0
        }
      };
      
      // Get transaction pool stats
      if (transactionPool) {
        const poolStats = transactionPool.getStats();
        stats.pending = poolStats.count;
        stats.feeStats = poolStats.fees || { average: 0, min: 0, max: 0 };
      }
      
      // Get database stats
      if (pgClient) {
        // Total transactions
        const txResult = await pgClient.query('SELECT COUNT(*) as count FROM transactions');
        stats.total = parseInt(txResult.rows[0].count, 10);
        
        // Transactions in last 24 hours
        const tx24Result = await pgClient.query(
          'SELECT COUNT(*) as count FROM transactions WHERE timestamp > NOW() - INTERVAL \'24 hours\''
        );
        stats.last24Hours = parseInt(tx24Result.rows[0].count, 10);
        
        // Transactions per day for last 30 days
        const txPerDayResult = await pgClient.query(
          `SELECT 
            DATE(timestamp) as day,
            COUNT(*) as tx_count
          FROM transactions
          WHERE timestamp > NOW() - INTERVAL '30 days'
          GROUP BY DATE(timestamp)
          ORDER BY day ASC`
        );
        
        stats.transactionsPerDay = txPerDayResult.rows.map(row => ({
          day: row.day,
          count: parseInt(row.tx_count, 10)
        }));
        
        // Fee statistics
        const feeResult = await pgClient.query(
          `SELECT 
            AVG(fee) as avg_fee,
            MIN(fee) as min_fee,
            MAX(fee) as max_fee
          FROM transactions
          WHERE timestamp > NOW() - INTERVAL '24 hours'`
        );
        
        if (feeResult.rows.length > 0) {
          stats.feeStats.average = parseFloat(feeResult.rows[0].avg_fee) || 0;
          stats.feeStats.min = parseFloat(feeResult.rows[0].min_fee) || 0;
          stats.feeStats.max = parseFloat(feeResult.rows[0].max_fee) || 0;
        }
      }
      
      res.json(stats);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get validator statistics
   * GET /api/v1/stats/validators
   */
  router.get('/validators', async (req, res, next) => {
    try {
      // Initialize stats object
      const stats = {
        timestamp: Date.now(),
        total: 0,
        active: 0,
        jailed: 0,
        inactive: 0,
        tombstoned: 0,
        totalStake: 0,
        topValidators: []
      };
      
      // Get database stats
      if (pgClient) {
        // Validator counts
        const validatorResult = await pgClient.query(
          'SELECT status, COUNT(*) as count FROM validators GROUP BY status'
        );
        
        validatorResult.rows.forEach(row => {
          stats.total += parseInt(row.count, 10);
          
          if (row.status === 'active') {
            stats.active = parseInt(row.count, 10);
          } else if (row.status === 'jailed') {
            stats.jailed = parseInt(row.count, 10);
          } else if (row.status === 'inactive') {
            stats.inactive = parseInt(row.count, 10);
          } else if (row.status === 'tombstoned') {
            stats.tombstoned = parseInt(row.count, 10);
          }
        });
        
        // Total stake
        const stakeResult = await pgClient.query('SELECT SUM(stake) as total_stake FROM validators');
        stats.totalStake = parseFloat(stakeResult.rows[0].total_stake) || 0;
        
        // Top validators by stake
        const topResult = await pgClient.query(
          'SELECT address, stake, status FROM validators ORDER BY stake DESC LIMIT 20'
        );
        
        stats.topValidators = topResult.rows.map(row => ({
          address: row.address,
          stake: parseFloat(row.stake),
          status: row.status
        }));
      }
      
      res.json(stats);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * Get distribution period statistics
   * GET /api/v1/stats/distribution
   */
  router.get('/distribution', async (req, res, next) => {
    try {
      // Get distribution status
      if (!stateMachine) {
        return res.status(503).json({
          error: 'State machine not available'
        });
      }
      
      const distributionStatus = await stateMachine.getDistributionStatus();
      
      // Get validator rewards
      let validatorRewards = [];
      
      if (pgClient) {
        const rewardsResult = await pgClient.query(
          `SELECT 
            validator_address,
            SUM(amount) as total_rewards,
            COUNT(*) as reward_count
          FROM rewards
          WHERE type = 'distribution'
          GROUP BY validator_address
          ORDER BY total_rewards DESC`
        );
        
        validatorRewards = rewardsResult.rows.map(row => ({
          address: row.validator_address,
          totalRewards: parseFloat(row.total_rewards),
          rewardCount: parseInt(row.reward_count, 10)
        }));
      }
      
      res.json({
        ...distributionStatus,
        validatorRewards
      });
    } catch (error) {
      next(error);
    }
  });
  
  return router;
}

module.exports = createStatsRoutes;
