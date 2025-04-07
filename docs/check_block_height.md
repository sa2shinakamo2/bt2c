# BT2C Block Height Checker

The `check_block_height.py` script allows you to check the current block height and latest block details of the BT2C blockchain.

## Usage

```bash
python tools/check_block_height.py [options]
```

### Options

- `--network NETWORK`: Specify the network type (mainnet or testnet). Default is mainnet.
- `--verbose`: Show detailed information about the latest block.

## Examples

### Check Basic Block Height

```bash
python tools/check_block_height.py
```

Output:
```
🔗 BT2C MAINNET Blockchain
====================================
Current Block Height: 100
Total Blocks: 101
```

### Check Block Height with Detailed Information

```bash
python tools/check_block_height.py --verbose
```

Output:
```
🔗 BT2C MAINNET Blockchain
====================================
Current Block Height: 100
Total Blocks: 101

📦 Latest Block Details:
  Height: 100
  Hash: abcdef1234...
  Timestamp: 1743984000.12345
  Merkle Root: 1234567890...
```

### Check Block Height on Testnet

```bash
python tools/check_block_height.py --network testnet
```

## Technical Details

The script connects to the BT2C blockchain database located at `~/.bt2c/data/blockchain.db` and performs the following operations:

1. Queries the maximum block height in the blockchain
2. Counts the total number of blocks in the blockchain
3. Retrieves details about the latest block if the `--verbose` flag is provided

## Block Information

When using the `--verbose` flag, the script provides the following information about the latest block:

- **Height**: The block number/height
- **Hash**: The unique identifier of the block (truncated for readability)
- **Timestamp**: The Unix timestamp when the block was created
- **Merkle Root**: The root hash of the Merkle tree containing all transactions in the block (truncated for readability)

## Error Handling

The script handles the following error cases:

- Database not found
- Database connection issues
- Empty blockchain (no blocks)
- Network type not found

## Dependencies

- Python 3.8+
- SQLite3
- BT2C blockchain database

## Integration with Other Tools

The `check_block_height.py` script can be used in conjunction with other BT2C tools:

- Use with `check_wallet_balance.py` to verify if transactions have been included in blocks
- Use with `view_blockchain.py` to get more detailed information about specific blocks
- Use with `produce_blocks_scheduled.py` to monitor block production progress

## Monitoring Block Production

This tool is particularly useful for validators to monitor the progress of block production. By running the script at regular intervals, validators can ensure that blocks are being produced at the expected 5-minute intervals as specified in the BT2C whitepaper.
