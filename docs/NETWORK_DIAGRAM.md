# BT2C Network Architecture Diagram

This document provides visual representations of the BT2C network architecture to help understand how validators, seed nodes, and other components interact.

## Current Network Topology

The current BT2C network uses a simplified architecture where the developer node serves as both a validator and seed node.

```mermaid
graph TD
    subgraph "BT2C Network"
        DN[Developer Node<br/>Validator + Seed Node<br/>bt2c.network:8334] 
        
        V1[Validator 1]
        V2[Validator 2]
        V3[Validator 3]
        V4[Validator 4]
        V5[Validator 5]
        
        DN <--> V1
        DN <--> V2
        DN <--> V3
        DN <--> V4
        DN <--> V5
        
        V1 <--> V2
        V2 <--> V3
        V3 <--> V4
        V4 <--> V5
        V5 <--> V1
        V1 <--> V3
        V2 <--> V4
        V3 <--> V5
    end
    
    NV[New Validator] -.-> DN
    
    classDef devNode fill:#f9f,stroke:#333,stroke-width:2px;
    classDef validator fill:#bbf,stroke:#333,stroke-width:1px;
    classDef newValidator fill:#bfb,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5;
    
    class DN devNode;
    class V1,V2,V3,V4,V5 validator;
    class NV newValidator;
```

## Network Components

### Validator Node Configuration

```mermaid
graph TD
    subgraph "Validator Node"
        BC[Blockchain Core]
        API[API Server]
        P2P[P2P Network]
        CONS[Consensus Engine]
        MEM[Mempool]
        PROM[Prometheus Metrics]
        GRAF[Grafana Dashboard]
        
        BC <--> API
        BC <--> P2P
        BC <--> CONS
        BC <--> MEM
        PROM --> GRAF
        BC --> PROM
    end
    
    classDef core fill:#f96,stroke:#333,stroke-width:2px;
    classDef component fill:#9cf,stroke:#333,stroke-width:1px;
    classDef monitoring fill:#9f9,stroke:#333,stroke-width:1px;
    
    class BC core;
    class API,P2P,CONS,MEM component;
    class PROM,GRAF monitoring;
```

## Data Flow

The following diagram illustrates how data flows through the BT2C network:

```mermaid
sequenceDiagram
    participant User
    participant API as API Server
    participant Validator as Validator Node
    participant Network as BT2C Network
    
    User->>API: Submit Transaction
    API->>Validator: Validate Transaction
    Validator->>Validator: Add to Mempool
    Validator->>Network: Broadcast Transaction
    Network->>Network: Consensus Process
    Network->>Validator: Block Creation
    Validator->>Network: Broadcast New Block
    Network->>API: Update State
    API->>User: Transaction Confirmed
```

## Validator States

BT2C validators can transition between different states:

```mermaid
stateDiagram-v2
    [*] --> Inactive: Register
    Inactive --> Active: Stake Tokens
    Active --> Inactive: Unstake All
    Active --> Jailed: Miss Blocks
    Jailed --> Active: Wait Unjail Period
    Jailed --> Tombstoned: Severe Violation
    Tombstoned --> [*]: Permanent Ban
    
    note right of Active
        Earning rewards
        Participating in consensus
    end note
    
    note right of Jailed
        Temporary suspension
        No rewards
        Affects reputation
    end note
```

## Network Growth Plan

As the BT2C network grows, the architecture will evolve:

```mermaid
graph TD
    subgraph "Current (March 2025)"
        DN1[Developer Node<br/>Validator + Seed]
        V1[Validator]
        V2[Validator]
        DN1 <--> V1
        DN1 <--> V2
        V1 <--> V2
    end
    
    subgraph "Phase 2 (Q2 2025)"
        DN2[Developer Node<br/>Validator + Seed]
        S1[Dedicated Seed Node 1]
        S2[Dedicated Seed Node 2]
        V3[Validator]
        V4[Validator]
        V5[Validator]
        
        DN2 <--> S1
        DN2 <--> S2
        S1 <--> S2
        
        S1 <--> V3
        S1 <--> V4
        S2 <--> V4
        S2 <--> V5
        
        V3 <--> V4
        V4 <--> V5
    end
    
    subgraph "Phase 3 (Q4 2025)"
        S3[Seed Node 1]
        S4[Seed Node 2]
        S5[Seed Node 3]
        S6[Seed Node 4]
        
        V6[Validator]
        V7[Validator]
        V8[Validator]
        V9[Validator]
        V10[Validator]
        
        S3 <--> S4
        S4 <--> S5
        S5 <--> S6
        S6 <--> S3
        
        S3 <--> V6
        S3 <--> V7
        S4 <--> V7
        S4 <--> V8
        S5 <--> V8
        S5 <--> V9
        S6 <--> V9
        S6 <--> V10
        
        V6 <--> V7
        V7 <--> V8
        V8 <--> V9
        V9 <--> V10
        V10 <--> V6
    end
    
    Current --> Phase2
    Phase2 --> Phase3
    
    classDef current fill:#bbf,stroke:#333,stroke-width:1px;
    classDef phase2 fill:#bfb,stroke:#333,stroke-width:1px;
    classDef phase3 fill:#fbf,stroke:#333,stroke-width:1px;
    
    class Current current;
    class Phase2 phase2;
    class Phase3 phase3;
```

## Reputation System Impact

The reputation system affects validator selection and rewards:

```mermaid
graph LR
    subgraph "Reputation Factors"
        UP[Uptime]
        BV[Block Validation<br/>Accuracy]
        RT[Response Time]
        TP[Transaction<br/>Processing]
    end
    
    subgraph "Impact Areas"
        VS[Validator Selection]
        R[Rewards]
        EQ[Exit Queue]
    end
    
    UP --> RS
    BV --> RS
    RT --> RS
    TP --> RS
    
    RS[Reputation Score] --> VS
    RS --> R
    RS --> EQ
    
    classDef factor fill:#ffd,stroke:#333,stroke-width:1px;
    classDef score fill:#f96,stroke:#333,stroke-width:2px;
    classDef impact fill:#9cf,stroke:#333,stroke-width:1px;
    
    class UP,BV,RT,TP factor;
    class RS score;
    class VS,R,EQ impact;
```

## Notes on Diagram Usage

These diagrams are intended to provide a visual understanding of the BT2C network architecture. They can be viewed in any Markdown viewer that supports Mermaid diagrams, or by using the Mermaid Live Editor at [https://mermaid.live](https://mermaid.live).

For the most up-to-date information about the BT2C network architecture, refer to the [NETWORK_ARCHITECTURE.md](NETWORK_ARCHITECTURE.md) document.
