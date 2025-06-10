#!/usr/bin/env python3
"""
BT2C Whitepaper PDF Generator
This script converts the BT2C whitepaper markdown to a PDF in the style of the Bitcoin whitepaper.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Define the output path
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bt2c.pdf')

# Create the PDF document
doc = SimpleDocTemplate(output_path, pagesize=A4, 
                        rightMargin=72, leftMargin=72,
                        topMargin=72, bottomMargin=72)

# Get the standard stylesheet
styles = getSampleStyleSheet()

# Create custom styles
styles.add(ParagraphStyle(name='BT2CTitle',
                         parent=styles['Title'],
                         fontSize=18,
                         spaceAfter=12))

styles.add(ParagraphStyle(name='BT2CAbstract',
                         parent=styles['Normal'],
                         fontSize=10,
                         spaceAfter=12,
                         leading=14))

styles.add(ParagraphStyle(name='BT2CHeading1',
                         parent=styles['Heading1'],
                         fontSize=14,
                         spaceAfter=10))

styles.add(ParagraphStyle(name='BT2CHeading2',
                         parent=styles['Heading2'],
                         fontSize=12,
                         spaceAfter=8))

styles.add(ParagraphStyle(name='BT2CNormal',
                         parent=styles['Normal'],
                         fontSize=10,
                         spaceAfter=8,
                         leading=14))

# Content elements
content = []

# Title
content.append(Paragraph("BT2C: A Pure Cryptocurrency Implementation with Reputation-Based Proof of Stake", styles['BT2CTitle']))
content.append(Spacer(1, 0.2*inch))
content.append(Paragraph("BT2C Core Development Team", styles['BT2CNormal']))
content.append(Paragraph("March 19, 2025", styles['BT2CNormal']))
content.append(Spacer(1, 0.5*inch))

# Abstract
content.append(Paragraph("<b>Abstract.</b> This paper introduces BT2C (bit2coin), a cryptocurrency designed to function as a pure medium of exchange and store of value without the overhead of smart contracts or decentralized applications. We present a novel reputation-based Proof of Stake (rPoS) consensus mechanism that addresses the energy consumption concerns of Proof of Work while maintaining security properties through cryptographic verification and economic incentives. BT2C implements a deterministic issuance schedule with a fixed maximum supply, combined with a flexible staking model that optimizes for network security and validator participation. This paper outlines the technical architecture, cryptographic foundations, consensus rules, and economic model of the BT2C network.", styles['BT2CAbstract']))
content.append(Spacer(1, 0.2*inch))

# Introduction
content.append(Paragraph("1. Introduction", styles['BT2CHeading1']))
content.append(Paragraph("Cryptocurrencies have evolved significantly since the introduction of Bitcoin in 2009. While many projects have expanded into complex platforms supporting smart contracts and decentralized applications, BT2C returns to the original vision of a peer-to-peer electronic cash system with improvements in energy efficiency, transaction finality, and participation accessibility.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("The core innovation of BT2C lies in its reputation-based Proof of Stake consensus mechanism, which selects validators based on a combination of stake amount and historical performance metrics. This approach provides three key advantages:", styles['BT2CNormal']))
core_advantages = ListFlowable([
    ListItem(Paragraph("Energy efficiency compared to Proof of Work systems", styles['BT2CNormal'])),
    ListItem(Paragraph("Resistance to centralization through accessible validator requirements", styles['BT2CNormal'])),
    ListItem(Paragraph("Enhanced security through reputation-based incentives", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(core_advantages)
content.append(Spacer(1, 0.2*inch))

# System Architecture
content.append(Paragraph("2. System Architecture", styles['BT2CHeading1']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("2.1 Network Topology", styles['BT2CHeading2']))
content.append(Paragraph("BT2C implements a peer-to-peer network with specialized validator nodes responsible for block production. The network utilizes a gossip protocol for message propagation with the following components:", styles['BT2CNormal']))
network_components = ListFlowable([
    ListItem(Paragraph("Seed nodes: Entry points for new validators joining the network", styles['BT2CNormal'])),
    ListItem(Paragraph("Validator nodes: Full nodes with staked BT2C that participate in consensus", styles['BT2CNormal'])),
    ListItem(Paragraph("API nodes: Provide REST and WebSocket interfaces for client applications", styles['BT2CNormal'])),
    ListItem(Paragraph("Explorer nodes: Index and serve blockchain data for user interfaces", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(network_components)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("Network communication occurs over TCP/IP with mandatory TLS encryption. Each node maintains a connection pool with a configurable number of peers, with priority given to connections with validators having higher reputation scores.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("2.2 Data Structures", styles['BT2CHeading2']))
content.append(Paragraph("2.2.1 Blocks", styles['BT2CHeading2']))
content.append(Paragraph("Each block in the BT2C blockchain contains a header with metadata and a body with transactions. Block hashes are computed using SHA3-256 over the concatenation of critical block data including height, timestamp, merkle root, validator address, reward amount, and previous block hash.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("2.2.2 Transactions", styles['BT2CHeading2']))
content.append(Paragraph("Transactions in BT2C follow a simple structure with sender, recipient, amount, fee, nonce, timestamp, signature, and hash. Transaction hashes are computed using SHA3-256, and signatures are generated using the sender's private key.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("2.3 Cryptographic Foundations", styles['BT2CHeading2']))
crypto_foundations = ListFlowable([
    ListItem(Paragraph("Key generation: 2048-bit RSA key pairs", styles['BT2CNormal'])),
    ListItem(Paragraph("Address derivation: base58 encoded hash of public key", styles['BT2CNormal'])),
    ListItem(Paragraph("Transaction signing: RSA-PSS with SHA-256", styles['BT2CNormal'])),
    ListItem(Paragraph("Block and transaction hashing: SHA3-256", styles['BT2CNormal'])),
    ListItem(Paragraph("Seed phrases: BIP39 with 256-bit entropy (24 words)", styles['BT2CNormal'])),
    ListItem(Paragraph("HD wallet derivation: BIP44 path m/44'/999'/0'/0/n", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(crypto_foundations)
content.append(Spacer(1, 0.2*inch))

# Consensus Mechanism
content.append(Paragraph("3. Consensus Mechanism", styles['BT2CHeading1']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("3.1 Reputation-Based Proof of Stake (rPoS)", styles['BT2CHeading2']))
content.append(Paragraph("BT2C introduces a reputation-based Proof of Stake consensus mechanism that extends traditional PoS by incorporating historical performance metrics into validator selection. The probability of a validator being selected is determined by both their stake amount and reputation score.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("The reputation score is calculated based on block validation accuracy, uptime, transaction processing efficiency, and historical participation quality. This formula ensures that even validators with poor reputation maintain a minimum selection probability, while high-performing validators can achieve up to 200% of their stake-based probability.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("3.2 Block Production", styles['BT2CHeading2']))
content.append(Paragraph("Block production in BT2C follows a time-based schedule with a target block time of 60 seconds. The selected validator has 30 seconds to produce and broadcast a valid block, after which a new validator is selected if necessary.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("3.3 Block Validation", styles['BT2CHeading2']))
block_validation = ListFlowable([
    ListItem(Paragraph("Verify the block structure and hash", styles['BT2CNormal'])),
    ListItem(Paragraph("Verify the selected validator's eligibility", styles['BT2CNormal'])),
    ListItem(Paragraph("Verify each transaction's signature and validity", styles['BT2CNormal'])),
    ListItem(Paragraph("Verify the Merkle root matches the transactions", styles['BT2CNormal'])),
    ListItem(Paragraph("Verify the block reward calculation", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(block_validation)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("A block is considered finalized when it has been built upon by 6 subsequent blocks, providing probabilistic finality similar to Bitcoin but with significantly shorter confirmation times due to the 60-second block interval.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("3.4 Validator States", styles['BT2CHeading2']))
content.append(Paragraph("Validators in BT2C can exist in four distinct states: Active, Inactive, Jailed, or Tombstoned. Transitions between states follow specific rules based on validator behavior and protocol compliance.", styles['BT2CNormal']))
content.append(Spacer(1, 0.2*inch))

# Economic Model
content.append(Paragraph("4. Economic Model", styles['BT2CHeading1']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("4.1 Supply Schedule", styles['BT2CHeading2']))
supply_schedule = ListFlowable([
    ListItem(Paragraph("Maximum supply: 21,000,000 BT2C", styles['BT2CNormal'])),
    ListItem(Paragraph("Initial block reward: 21.0 BT2C", styles['BT2CNormal'])),
    ListItem(Paragraph("Halving interval: 4 years (approximately 2,102,400 blocks)", styles['BT2CNormal'])),
    ListItem(Paragraph("Minimum reward: 0.00000001 BT2C", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(supply_schedule)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("4.2 Fee Market", styles['BT2CHeading2']))
content.append(Paragraph("Transaction fees in BT2C are dynamic, based on network congestion. The minimum fee increases with network utilization, ensuring fees remain low during normal operation but increase during periods of high demand to prioritize transactions efficiently.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("4.3 Staking Economics", styles['BT2CHeading2']))
staking_economics = ListFlowable([
    ListItem(Paragraph("Minimum stake: 1.0 BT2C", styles['BT2CNormal'])),
    ListItem(Paragraph("No maximum stake: Validators can stake any amount above the minimum", styles['BT2CNormal'])),
    ListItem(Paragraph("No fixed staking period: Validators can unstake at any time", styles['BT2CNormal'])),
    ListItem(Paragraph("Unstaking queue: Withdrawals enter a FIFO queue processed over time", styles['BT2CNormal'])),
    ListItem(Paragraph("Queue processing rate: Limited to 1% of total stake per day", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(staking_economics)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("4.4 Validator Incentives", styles['BT2CHeading2']))
validator_incentives = ListFlowable([
    ListItem(Paragraph("Developer Node Reward: 1000 BT2C (one-time reward for first mainnet validator)", styles['BT2CNormal'])),
    ListItem(Paragraph("Early Validator Reward: 1.0 BT2C (for validators joining during distribution period)", styles['BT2CNormal'])),
    ListItem(Paragraph("Distribution Period: 14 days from mainnet launch", styles['BT2CNormal'])),
    ListItem(Paragraph("Auto-staking: All distribution period rewards are automatically staked", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(validator_incentives)
content.append(Spacer(1, 0.2*inch))

# Security Considerations
content.append(Paragraph("5. Security Considerations", styles['BT2CHeading1']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("5.1 Sybil Resistance", styles['BT2CHeading2']))
content.append(Paragraph("The minimum stake requirement of 1.0 BT2C provides a basic economic barrier against Sybil attacks. Additionally, the reputation system requires consistent participation over time to achieve maximum influence, making it costly to establish multiple high-reputation validators.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("5.2 Nothing-at-Stake Problem", styles['BT2CHeading2']))
nothing_at_stake = ListFlowable([
    ListItem(Paragraph("Slashing conditions: Validators who sign conflicting blocks lose a portion of their stake", styles['BT2CNormal'])),
    ListItem(Paragraph("Reputation penalties: Double-signing results in immediate reputation reduction to minimum", styles['BT2CNormal'])),
    ListItem(Paragraph("Tombstoning: Severe violations result in permanent exclusion from the validator set", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(nothing_at_stake)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("5.3 Long-Range Attacks", styles['BT2CHeading2']))
long_range_attacks = ListFlowable([
    ListItem(Paragraph("Weak subjectivity checkpoints: Published every 10,000 blocks", styles['BT2CNormal'])),
    ListItem(Paragraph("Time-bound validator set changes: Validator set changes take effect only after a delay", styles['BT2CNormal'])),
    ListItem(Paragraph("Social consensus backstop: Community-recognized canonical chain in case of deep reorganizations", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(long_range_attacks)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("5.4 Transaction Replay Protection", styles['BT2CHeading2']))
content.append(Paragraph("Each transaction includes a unique nonce derived from the sender's account state, preventing transaction replay attacks. The nonce is incremented with each transaction, and the network rejects transactions with previously used nonces.", styles['BT2CNormal']))
content.append(Spacer(1, 0.2*inch))

# Implementation Details
content.append(Paragraph("6. Implementation Details", styles['BT2CHeading1']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("6.1 Core Components", styles['BT2CHeading2']))
core_components = ListFlowable([
    ListItem(Paragraph("Consensus engine: Implements the rPoS algorithm and block validation rules", styles['BT2CNormal'])),
    ListItem(Paragraph("Transaction pool: Manages pending transactions and fee prioritization", styles['BT2CNormal'])),
    ListItem(Paragraph("State machine: Tracks account balances, stakes, and validator metadata", styles['BT2CNormal'])),
    ListItem(Paragraph("P2P network: Handles peer discovery and message propagation", styles['BT2CNormal'])),
    ListItem(Paragraph("API server: Provides external interfaces for clients and services", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(core_components)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("6.2 Data Persistence", styles['BT2CHeading2']))
data_persistence = ListFlowable([
    ListItem(Paragraph("Blockchain data: Stored in a custom append-only file format optimized for sequential access", styles['BT2CNormal'])),
    ListItem(Paragraph("State data: Maintained in a PostgreSQL database for efficient querying and indexing", styles['BT2CNormal'])),
    ListItem(Paragraph("Mempool: Held in memory with Redis backup for persistence across restarts", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(data_persistence)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("6.3 Performance Optimizations", styles['BT2CHeading2']))
performance_optimizations = ListFlowable([
    ListItem(Paragraph("Parallel transaction verification: Multiple CPU cores validate transaction signatures concurrently", styles['BT2CNormal'])),
    ListItem(Paragraph("Incremental state updates: State changes are applied incrementally rather than recomputing", styles['BT2CNormal'])),
    ListItem(Paragraph("Bloom filters: Used to quickly check transaction existence without full lookups", styles['BT2CNormal'])),
    ListItem(Paragraph("Connection pooling: Database connections are pooled for efficient resource utilization", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(performance_optimizations)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("6.4 Network Parameters", styles['BT2CHeading2']))
network_parameters = ListFlowable([
    ListItem(Paragraph("Target block time: 60 seconds", styles['BT2CNormal'])),
    ListItem(Paragraph("Maximum block size: 1MB", styles['BT2CNormal'])),
    ListItem(Paragraph("Transaction throughput: Up to 100 tx/s", styles['BT2CNormal'])),
    ListItem(Paragraph("Rate limiting: 100 requests/minute", styles['BT2CNormal'])),
    ListItem(Paragraph("Network ports: 26656 (P2P), 26660 (metrics)", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(network_parameters)
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("6.5 Infrastructure Requirements", styles['BT2CHeading2']))
infrastructure_requirements = ListFlowable([
    ListItem(Paragraph("Hardware: 4 CPU cores, 8GB RAM, 100GB SSD", styles['BT2CNormal'])),
    ListItem(Paragraph("Software: Docker & Docker Compose", styles['BT2CNormal'])),
    ListItem(Paragraph("Database: PostgreSQL", styles['BT2CNormal'])),
    ListItem(Paragraph("Caching: Redis", styles['BT2CNormal'])),
    ListItem(Paragraph("Monitoring: Prometheus & Grafana", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(infrastructure_requirements)
content.append(Spacer(1, 0.2*inch))

# Distribution Period Mechanics
content.append(Paragraph("7. Distribution Period Mechanics", styles['BT2CHeading1']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("To bootstrap the network securely, BT2C implemented a 14-day distribution period with special incentives:", styles['BT2CNormal']))
distribution_period = ListFlowable([
    ListItem(Paragraph("Early validator reward: 1.0 BT2C for any validator joining during this period", styles['BT2CNormal'])),
    ListItem(Paragraph("Developer node reward: 1000 BT2C for the first validator (network founder)", styles['BT2CNormal'])),
    ListItem(Paragraph("Automatic staking: All distribution rewards are automatically staked", styles['BT2CNormal'])),
], bulletType='bullet', start=None)
content.append(distribution_period)
content.append(Paragraph("These mechanics were designed to ensure sufficient initial stake distribution while maintaining security during the critical launch phase.", styles['BT2CNormal']))
content.append(Spacer(1, 0.2*inch))

# Conclusion
content.append(Paragraph("8. Conclusion", styles['BT2CHeading1']))
content.append(Paragraph("BT2C represents a focused approach to cryptocurrency design, combining Bitcoin's economic principles with modern consensus mechanisms. By implementing reputation-based Proof of Stake, BT2C achieves energy efficiency without sacrificing security or decentralization.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("The deliberate exclusion of smart contracts and complex programmability allows BT2C to optimize for its core use case: a secure, efficient medium of exchange and store of value. This specialization enables performance optimizations and security hardening that would be challenging in more general-purpose blockchain platforms.", styles['BT2CNormal']))
content.append(Spacer(1, 0.1*inch))

content.append(Paragraph("As the network continues to mature beyond its initial distribution period, the reputation system will increasingly reward consistent, high-quality participation, creating a virtuous cycle of improved security and performance.", styles['BT2CNormal']))

# Build the PDF
doc.build(content)

print(f"PDF generated successfully at {output_path}")
