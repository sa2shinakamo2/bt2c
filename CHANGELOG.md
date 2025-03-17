# BT2C Changelog

All notable changes to the BT2C blockchain will be documented in this file.

## [1.1.0] - 2025-03-17

### Security Enhancements
- **Nonce Validation**
  - Added tracking of transaction nonces per sender address
  - Implemented validation to ensure strictly increasing nonces
  - Updated transaction creation script to automatically fetch and increment nonces
  - Prevents transaction replay attacks

- **Double-Spend Protection**
  - Added a spent transaction tracker to prevent double-spending
  - Implemented validation to reject transactions that have already been processed
  - Enhanced transaction validation checks

- **Transaction Finality Rules**
  - Defined clear transaction finality states:
    - Pending: Not yet included in a block
    - Tentative: 1-2 confirmations
    - Probable: 3-5 confirmations
    - Final: 6+ confirmations
  - Added finality information to transaction responses
  - Updated API to expose finality status in transaction queries

- **Mempool Cleanup**
  - Added mechanism to remove transactions from the pending pool once included in a block
  - Implemented logging for tracking removed and remaining transactions
  - Prevents double-processing of transactions

### API Improvements
- Added transaction endpoints with finality information
- Improved error handling and validation
- Added blockchain status endpoint
- Added wallet information endpoint

### Testing
- Added security verification script to test security features
- Improved test coverage for transaction processing

## [1.0.0] - 2025-02-15

### Initial Release
- Core blockchain functionality
- Proof of Stake consensus mechanism
- Validator staking and rewards
- Dynamic validator participation
- Automated reward distribution
- Basic transaction processing
- Genesis configuration
- Network synchronization
- P2P communication
- Basic API endpoints
- Wallet management
