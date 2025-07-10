/**
 * BT2C Message Types
 * 
 * This module defines all message types used in the BT2C network protocol.
 */

/**
 * Message types enum
 * @enum {string}
 */
const MessageType = {
  // Connection management
  HANDSHAKE: 'handshake',
  PING: 'ping',
  PONG: 'pong',
  
  // Peer discovery
  GET_PEERS: 'get_peers',
  PEERS: 'peers',
  
  // Block synchronization
  GET_BLOCKS: 'get_blocks',
  BLOCKS: 'blocks',
  NEW_BLOCK: 'new_block',
  
  // Transaction management
  GET_TRANSACTIONS: 'get_transactions',
  TRANSACTIONS: 'transactions',
  NEW_TRANSACTION: 'new_transaction',
  
  // Validator management
  VALIDATOR_UPDATE: 'validator_update',
  
  // Version and feature negotiation
  VERSION: 'version',
  VERACK: 'verack',
  
  // Address management (Bitcoin-style)
  ADDR: 'addr',
  GETADDR: 'getaddr'
};

module.exports = {
  MessageType
};
