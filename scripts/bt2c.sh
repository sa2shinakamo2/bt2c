#!/bin/bash

# BT2C CLI tool for checking balances and validator status
# Usage: ./bt2c.sh balance <wallet_address>
#        ./bt2c.sh status
#        ./bt2c.sh validators

# Configuration
VALIDATOR1_URL="http://localhost:8081"
VALIDATOR2_URL="http://localhost:8082"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

check_balance() {
    local wallet=$1
    echo -e "${BLUE}Checking balance for wallet: $wallet${NC}"
    
    # Try validator1
    response=$(curl -s $VALIDATOR1_URL/api/v1/wallet/balance?address=$wallet)
    if [ $? -eq 0 ] && [ ! -z "$response" ]; then
        balance=$(echo $response | jq -r '.balance // "N/A"')
        staked=$(echo $response | jq -r '.staked // "0"')
        rewards=$(echo $response | jq -r '.rewards // "0"')
        echo -e "${GREEN}Balance: $balance BT2C${NC}"
        echo -e "${GREEN}Staked: $staked BT2C${NC}"
        echo -e "${GREEN}Rewards: $rewards BT2C${NC}"
    else
        # Try validator2
        response=$(curl -s $VALIDATOR2_URL/api/v1/wallet/balance?address=$wallet)
        if [ $? -eq 0 ] && [ ! -z "$response" ]; then
            balance=$(echo $response | jq -r '.balance // "N/A"')
            staked=$(echo $response | jq -r '.staked // "0"')
            rewards=$(echo $response | jq -r '.rewards // "0"')
            echo -e "${GREEN}Balance: $balance BT2C${NC}"
            echo -e "${GREEN}Staked: $staked BT2C${NC}"
            echo -e "${GREEN}Rewards: $rewards BT2C${NC}"
        else
            echo -e "${RED}Error: Could not fetch balance${NC}"
        fi
    fi
}

check_status() {
    echo -e "${BLUE}Checking validator status...${NC}"
    
    # Try validator1
    response=$(curl -s $VALIDATOR1_URL/api/v1/status)
    if [ $? -eq 0 ] && [ ! -z "$response" ]; then
        echo -e "\n${GREEN}Validator 1 Status:${NC}"
        network=$(echo $response | jq -r '.network // "bt2c-mainnet-1"')
        block_height=$(echo $response | jq -r '.block_height // "0"')
        total_stake=$(echo $response | jq -r '.total_stake // "0"')
        block_time=$(echo $response | jq -r '.block_time // "300"')
        distribution_active=$(echo $response | jq -r '.distribution_active // "true"')
        
        echo -e "Network: $network"
        echo -e "Block Height: $block_height"
        echo -e "Total Stake: $total_stake BT2C"
        echo -e "Block Time: ${block_time}s"
        
        if [ "$distribution_active" = "true" ]; then
            echo -e "\n${YELLOW}Distribution Period Active:${NC}"
            remaining_days=$(echo $response | jq -r '.distribution_days_remaining // "14"')
            validators=$(echo $response | jq -r '.early_validator_count // "0"')
            rewards=$(echo $response | jq -r '.total_rewards_distributed // "0"')
            echo -e "Days Remaining: $remaining_days"
            echo -e "Early Validators: $validators"
            echo -e "Total Rewards: $rewards BT2C"
        fi
    else
        echo -e "${RED}Error: Could not fetch validator 1 status${NC}"
    fi
    
    # Try validator2
    response=$(curl -s $VALIDATOR2_URL/api/v1/status)
    if [ $? -eq 0 ] && [ ! -z "$response" ]; then
        echo -e "\n${GREEN}Validator 2 Status:${NC}"
        network=$(echo $response | jq -r '.network // "bt2c-mainnet-1"')
        block_height=$(echo $response | jq -r '.block_height // "0"')
        total_stake=$(echo $response | jq -r '.total_stake // "0"')
        block_time=$(echo $response | jq -r '.block_time // "300"')
        
        echo -e "Network: $network"
        echo -e "Block Height: $block_height"
        echo -e "Total Stake: $total_stake BT2C"
        echo -e "Block Time: ${block_time}s"
    else
        echo -e "${RED}Error: Could not fetch validator 2 status${NC}"
    fi
}

check_validators() {
    echo -e "${BLUE}Checking validator information...${NC}"
    
    # Check validator1
    response=$(curl -s $VALIDATOR1_URL/api/v1/validators)
    if [ $? -eq 0 ] && [ ! -z "$response" ]; then
        echo -e "\n${GREEN}Active Validators:${NC}"
        echo "$response" | jq -r '.validators[] | "Address: \(.address)\nType: \(.type)\nStake: \(.stake) BT2C\nUptime: \(.uptime)%\nBlocks: \(.blocks_validated)\n"'
    else
        echo -e "${RED}Error: Could not fetch validator information${NC}"
    fi
}

case "$1" in
    "balance")
        if [ -z "$2" ]; then
            echo "Error: Wallet address required"
            echo "Usage: $0 balance <wallet_address>"
            exit 1
        fi
        check_balance "$2"
        ;;
    "status")
        check_status
        ;;
    "validators")
        check_validators
        ;;
    *)
        echo -e "${BLUE}BT2C CLI Tool${NC}"
        echo "Usage:"
        echo "  $0 balance <wallet_address>  - Check wallet balance"
        echo "  $0 status                    - Check validator status"
        echo "  $0 validators                - List active validators"
        exit 1
        ;;
esac
