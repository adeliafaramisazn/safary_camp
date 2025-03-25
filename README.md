# safary_camp - Cross-Chain Bridge Event Listener

This repository contains a Python-based simulation of a critical component in a cross-chain bridge system: the event listener. This script is designed as a robust, architecturally sound service that monitors a source blockchain for specific events (e.g., asset deposits) and simulates the corresponding actions required on a destination chain.

## Concept

A cross-chain bridge allows users to transfer assets or data from one blockchain to another. A common architecture for this is a "lock-and-mint" or "burn-and-release" model. The event listener (often called a relayer, validator, or oracle) is the off-chain service that makes this possible.

Its core responsibilities are:
1.  **Monitor**: Continuously watch a specific smart contract on the source chain.
2.  **Detect**: Identify relevant events, such as `DepositInitiated`, which signify a user's intent to bridge assets.
3.  **Validate**: Verify the event's authenticity and details.
4.  **Relay**: Securely transmit the event information to the destination chain by submitting a new transaction (e.g., to a contract that will mint new tokens).

This script simulates this process by listening for events on a source chain and logging the actions it would take on the destination chain.

## Code Architecture

The script is designed with a clear separation of concerns, using several classes to manage different aspects of the process. This modular architecture makes the system easier to understand, maintain, and extend.

-   `BlockchainConnector`: Handles all direct communication with a blockchain's JSON-RPC endpoint. It encapsulates the `web3.py` instance and provides methods for checking connectivity and fetching chain data. An instance is created for both the source and destination chains.

-   `BridgeContractHandler`: This class is responsible for interacting with the specific bridge smart contract. It uses the `BlockchainConnector` and the contract's ABI to fetch and filter for specific events (like `DepositInitiated`) within a given range of blocks.

-   `CrossChainEventHandler`: This is the core business logic component. It receives decoded event data from the `BridgeContractHandler`, validates it, and determines the necessary action on the destination chain. To prevent replay attacks or duplicate processing, it maintains a set of processed transaction hashes. In this simulation, it logs the intended action (e.g., "Mint X tokens for user Y").

-   `EventListener`: The main orchestrator. It contains the primary run loop that drives the entire process. Its responsibilities include:
    -   Initializing all other components.
    -   Managing state, specifically persisting the `last_processed_block` number to a file (`listener_state.json`) to ensure it can resume from where it left off after a restart.
    -   Polling the source chain for new blocks at a regular interval.
    -   Coordinating the fetching of events and their subsequent processing.
    -   Handling graceful shutdowns (e.g., on `Ctrl+C`) to prevent state loss.

### Data Flow

The interaction between the classes follows a logical flow:

```
+---------------+
| EventListener | (Main Loop)
+---------------+
       | 1. Get latest block
       v
+---------------------+
| BlockchainConnector | (Source Chain)
+---------------------+
       |
       | 2. Fetch events in block range
       v
+-----------------------+
| BridgeContractHandler |
+-----------------------+
       |
       | 3. Pass each event for processing
       v
+------------------------+
| CrossChainEventHandler |
+------------------------+
       |
       | 4. Simulate action on destination chain
       v
+---------------------+
| BlockchainConnector | (Destination Chain - Simulated)
+---------------------+
```

## How it Works

1.  **Initialization**: Upon starting, the `EventListener` initializes connectors to both the source and destination chains. It then attempts to load its state from `listener_state.json`. If the file exists, it resumes from the last processed block. If not, it starts from the current latest block on the source chain.

2.  **Polling Loop**: The listener enters an infinite loop. In each cycle, it queries the source chain for its current latest block number.

3.  **Block Processing**: If the latest block number is greater than the last processed block, the listener begins processing the new blocks in manageable chunks (defined by `BLOCK_PROCESSING_CHUNK_SIZE`). This prevents making RPC requests that are too large.

4.  **Event Fetching**: For each chunk of blocks, the `BridgeContractHandler` queries the bridge contract for any `DepositInitiated` events that occurred within that range.

5.  **Event Handling**: If any events are found, they are passed one by one to the `CrossChainEventHandler`. The handler checks the event's transaction hash against an in-memory set to ensure it hasn't already been processed in the current session. 

6.  **Action Simulation**: For each new, valid event, the handler logs a detailed message describing the transaction that it would create and send on the destination chain. This includes the recipient's address and the amount of tokens to be minted or unlocked.

7.  **State Persistence**: After successfully processing a chunk of blocks, the `EventListener` updates its state with the latest block number it has scanned and saves this state to `listener_state.json`.

8.  **Wait**: The listener then sleeps for a configured interval (`LISTENER_POLL_INTERVAL_SECONDS`) before starting the cycle again.

## Usage Example

### 1. Prerequisites
- Python 3.8+
- `pip` and `venv`

### 2. Setup

First, clone the repository and navigate into the project directory:
```bash
git clone https://github.com/your-username/safary_camp.git
cd safary_camp
```

Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate
# On Windows, use: venv\Scripts\activate
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration

All configuration is located at the top of the `script.py` file. You can modify these constants directly.

-   `SOURCE_CHAIN_RPC_URL`: The RPC endpoint for the chain you want to listen to (e.g., an Infura or Alchemy URL for Sepolia).
-   `DESTINATION_CHAIN_RPC_URL`: The RPC endpoint for the destination chain.
-   `BRIDGE_CONTRACT_ADDRESS`: The address of the contract on the source chain that emits the events.

For production use, it is highly recommended to manage these secrets using a `.env` file and the `python-dotenv` library.

### 4. Running the Listener

Execute the script from your terminal:
```bash
python script.py
```

The listener will start, connect to the chains, and begin polling for new blocks and events.

### Example Output

```
2023-10-27 14:30:00 - INFO - Successfully connected to Chain ID 11155111 at https://rpc.sepolia.org
2023-10-27 14:30:01 - INFO - Successfully connected to Chain ID 80001 at https://rpc-mumbai.maticvigil.com
2023-10-27 14:30:01 - INFO - BridgeContractHandler initialized for contract at 0x7b79995e5f793A07Bc00c21412e50Eaae098E7f9
2023-10-27 14:30:01 - INFO - CrossChainEventHandler initialized.
2023-10-27 14:30:02 - INFO - Successfully loaded state. Last processed block: 4751020
2023-10-27 14:30:02 - INFO - Starting Cross-Chain Event Listener...
2023-10-27 14:30:05 - INFO - Processing blocks from 4751021 to 4751025
2023-10-27 14:30:08 - INFO - Found 1 'DepositInitiated' event(s) in blocks 4751021-4751025
2023-10-27 14:30:08 - INFO - Processing new event from transaction: 0xabc123...
2023-10-27 14:30:08 - INFO - [SIMULATION] Action required on Chain ID 80001:
2023-10-27 14:30:08 - INFO -   -> Mint/Unlock 1000000000000000000 tokens for recipient 0xRecipientAddress...
2023-10-27 14:30:08 - INFO -   -> Source Tx: 0xabc123..., Nonce: 12345
...
```