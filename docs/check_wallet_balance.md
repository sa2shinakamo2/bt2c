# BT2C Wallet Balance Checker

The `check_wallet_balance.py` script allows you to check the balance and transaction history of any BT2C wallet address.

## Usage

```bash
python tools/check_wallet_balance.py WALLET_ADDRESS [options]
```

### Arguments

- `WALLET_ADDRESS`: The BT2C wallet address to check (required)

### Options

- `--network NETWORK`: Specify the network type (mainnet or testnet). Default is mainnet.
- `--transactions`: Show recent transactions for the wallet.

## Examples

### Check Basic Wallet Balance

```bash
python tools/check_wallet_balance.py bt2c_example123456789abcdefghijk
```

Output:
```
💼 BT2C Wallet: bt2c_example123456789abcdefghijk
====================================
Network: mainnet
Balance: 42.000000 BT2C
Total Received: 42.000000 BT2C
Total Sent: 0.000000 BT2C
```

### Check Wallet Balance with Transaction History

```bash
python tools/check_wallet_balance.py bt2c_example123456789abcdefghijk --transactions
```

Output:
```
💼 BT2C Wallet: bt2c_example123456789abcdefghijk
====================================
Network: mainnet
Balance: 42.000000 BT2C
Total Received: 42.000000 BT2C
Total Sent: 0.000000 BT2C

📝 Recent Transactions:
---------------------

  RECEIVED 21.0 BT2C
  Received From: system
  Date: 2025-04-07 12:00:00
  Type: reward
  Hash: abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
  Block: #10
  Block Hash: abcdef1234...
  Status: Confirmed

  RECEIVED 21.0 BT2C
  Received From: system
  Date: 2025-04-07 11:55:00
  Type: reward
  Hash: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
  Block: #9
  Block Hash: 1234567890...
  Status: Confirmed
```

### Check Wallet Balance on Testnet

```bash
python tools/check_wallet_balance.py bt2c_example123456789abcdefghijk --network testnet
```

## Validator Information

If the wallet address is registered as a validator, additional validator information will be displayed:

```
🔐 Validator Information:
  Status: Active
  Stake: 1.0 BT2C
  Commission Rate: 10.0%
  Joined: 2025-04-07T00:00:00.000000
```

## Technical Details

The script connects to the BT2C blockchain database located at `~/.bt2c/data/blockchain.db` and performs the following operations:

1. Queries all transactions where the wallet address is either a sender or recipient
2. Calculates the total balance by summing all incoming and outgoing transactions
3. Retrieves validator information if the address is registered as a validator
4. Displays transaction history if the `--transactions` flag is provided

## Error Handling

The script handles the following error cases:

- Invalid wallet address format
- Wallet address not found in the blockchain
- Database connection issues
- Network type not found

## Dependencies

- Python 3.8+
- SQLite3
- BT2C blockchain database
