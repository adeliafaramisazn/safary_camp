import os
import json
import time
import logging
from typing import Dict, Any, List, Optional

import requests
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import BlockNotFound
from hexbytes import HexBytes

# ==============================================================================
# CONFIGURATION
# In a real application, use environment variables (e.g., via python-dotenv)
# ==============================================================================

# --- Source Chain (e.g., Ethereum Sepolia Testnet) ---
SOURCE_CHAIN_RPC_URL = "https://rpc.sepolia.org"
SOURCE_CHAIN_ID = 11155111

# --- Destination Chain (e.g., Polygon Mumbai Testnet) ---
# This is for simulation purposes; we'll only log the intended actions.
DESTINATION_CHAIN_RPC_URL = "https://rpc-mumbai.maticvigil.com"
DESTINATION_CHAIN_ID = 80001

# --- Bridge Contract Configuration ---
# This would be the address of your deployed bridge contract on the source chain.
# Using a known contract like the WETH address on Sepolia for a realistic ABI example.
BRIDGE_CONTRACT_ADDRESS = "0x7b79995e5f793A07Bc00c21412e50Eaae098E7f9" # Example: WETH on Sepolia

# A simplified ABI for a bridge contract, focusing on a deposit event.
BRIDGE_CONTRACT_ABI = json.loads('''
[
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "internalType": "address",
                "name": "sender",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "uint256",
                "name": "destinationChainId",
                "type": "uint256"
            },
            {
                "indexed": false,
                "internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "nonce",
                "type": "uint256"
            }
        ],
        "name": "DepositInitiated",
        "type": "event"
    }
]
''')

# --- Listener Configuration ---
LISTENER_POLL_INTERVAL_SECONDS = 15  # Time to wait between polling for new blocks
BLOCK_PROCESSING_CHUNK_SIZE = 100    # Number of blocks to process in one go
STATE_FILE_PATH = "listener_state.json"    # File to store the last processed block

# ==============================================================================
# LOGGING SETUP
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# CORE CLASSES
# ==============================================================================

class BlockchainConnector:
    """Handles connection and basic interactions with a blockchain via RPC."""

    def __init__(self, rpc_url: str, chain_id: int):
        """
        Initializes the connector with a given RPC endpoint.

        Args:
            rpc_url (str): The HTTP URL of the blockchain RPC endpoint.
            chain_id (int): The ID of the chain.
        """
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.web3: Optional[Web3] = None
        self.connect()

    def connect(self) -> None:
        """Establishes a connection to the RPC endpoint and verifies it."""
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if not self.web3.is_connected():
                raise ConnectionError(f"Failed to connect to RPC endpoint at {self.rpc_url}")
            logger.info(f"Successfully connected to Chain ID {self.chain_id} at {self.rpc_url}")
        except Exception as e:
            logger.error(f"Error connecting to {self.rpc_url}: {e}")
            self.web3 = None
            # In a production system, you might have retry logic with backoff here.
            raise

    def get_latest_block_number(self) -> int:
        """ 
        Retrieves the most recent block number from the blockchain.

        Returns:
            int: The latest block number.
        
        Raises:
            ConnectionError: If not connected to the blockchain.
        """
        if not self.web3 or not self.web3.is_connected():
            logger.warning("Attempted to get latest block while disconnected. Reconnecting...")
            self.connect()
        return self.web3.eth.block_number

    def get_contract_instance(self, address: str, abi: List[Dict[str, Any]]) -> Contract:
        """
        Creates a Web3.py Contract instance for interaction.

        Args:
            address (str): The contract's on-chain address.
            abi (List[Dict[str, Any]]): The contract's Application Binary Interface.

        Returns:
            Contract: A Web3.py contract object.
        """
        if not self.web3:
            raise ConnectionError("Web3 instance not available.")
        checksum_address = self.web3.to_checksum_address(address)
        return self.web3.eth.contract(address=checksum_address, abi=abi)


class BridgeContractHandler:
    """Manages interactions with a specific bridge contract, primarily for fetching events."""

    def __init__(self, connector: BlockchainConnector, contract_address: str, abi: List[Dict[str, Any]]):
        """
        Initializes the handler with a connector and contract details.

        Args:
            connector (BlockchainConnector): The connector for the source chain.
            contract_address (str): The address of the bridge contract.
            abi (List[Dict[str, Any]]): The ABI of the bridge contract.
        """
        self.connector = connector
        self.contract = self.connector.get_contract_instance(contract_address, abi)
        logger.info(f"BridgeContractHandler initialized for contract at {contract_address}")

    def fetch_events(self, event_name: str, from_block: int, to_block: int) -> List[Dict[str, Any]]:
        """
        Fetches specific events from the contract within a given block range.

        Args:
            event_name (str): The name of the event to fetch (e.g., 'DepositInitiated').
            from_block (int): The starting block number (inclusive).
            to_block (int): The ending block number (inclusive).

        Returns:
            List[Dict[str, Any]]: A list of decoded event logs.
        """
        logger.debug(f"Fetching '{event_name}' events from block {from_block} to {to_block}")
        try:
            event_filter = self.contract.events[event_name].create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            events = event_filter.get_all_entries()
            if events:
                logger.info(f"Found {len(events)} '{event_name}' event(s) in blocks {from_block}-{to_block}")
            return events
        except BlockNotFound:
            logger.warning(f"Block range {from_block}-{to_block} not found. The RPC node might be out of sync.")
            return []
        except requests.exceptions.ReadTimeout:
            logger.error(f"RPC timeout while fetching events for blocks {from_block}-{to_block}. Will retry.")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching events: {e}")
            return []


class CrossChainEventHandler:
    """Processes events from the source chain and simulates actions on the destination chain."""

    def __init__(self, destination_connector: BlockchainConnector):
        """
        Initializes the event handler.

        Args:
            destination_connector (BlockchainConnector): The connector for the destination chain.
        """
        self.destination_connector = destination_connector
        self.processed_events = set() # In-memory cache to prevent reprocessing during a single run
        logger.info("CrossChainEventHandler initialized.")

    def process_event(self, event: Dict[str, Any]) -> None:
        """
        Processes a single 'DepositInitiated' event.
        In a real system, this would trigger a signed transaction on the destination chain.

        Args:
            event (Dict[str, Any]): The event log data.
        """
        try:
            tx_hash_hex = event['transactionHash'].hex()
            if tx_hash_hex in self.processed_events:
                logger.warning(f"Event with tx_hash {tx_hash_hex} has already been processed in this session. Skipping.")
                return

            args = event['args']
            logger.info(f"Processing new event from transaction: {tx_hash_hex}")
            
            # --- Core Bridge Logic Simulation ---
            # 1. Validate the event data
            if args['destinationChainId'] != self.destination_connector.chain_id:
                logger.debug(f"Skipping event for incorrect destination chain ID {args['destinationChainId']}")
                return

            # 2. Construct the action for the destination chain
            # In a real scenario, you would use a private key to sign a transaction
            # to call a 'mint' or 'unlock' function on the destination bridge contract.
            logger.info(f"[SIMULATION] Action required on Chain ID {self.destination_connector.chain_id}:")
            logger.info(f"  -> Mint/Unlock {args['amount']} tokens for recipient {args['recipient']}.")
            logger.info(f"  -> Source Tx: {tx_hash_hex}, Nonce: {args['nonce']}")

            # 3. Mark as processed
            self.processed_events.add(tx_hash_hex)

        except Exception as e:
            logger.error(f"Failed to process event {event}: {e}")

class EventListener:
    """The main orchestrator that runs the event listening loop."""

    def __init__(self, source_connector: BlockchainConnector, dest_connector: BlockchainConnector,
                 bridge_handler: BridgeContractHandler, event_handler: CrossChainEventHandler):
        """
        Initializes the event listener with all necessary components.
        """
        self.source_connector = source_connector
        self.dest_connector = dest_connector
        self.bridge_handler = bridge_handler
        self.event_handler = event_handler
        self.state = {"last_processed_block": 0}
        self._load_state()

    def _load_state(self) -> None:
        """Loads the last processed block number from a state file."""
        try:
            if os.path.exists(STATE_FILE_PATH):
                with open(STATE_FILE_PATH, 'r') as f:
                    self.state = json.load(f)
                    logger.info(f"Successfully loaded state. Last processed block: {self.state['last_processed_block']}")
            else:
                logger.warning(f"State file not found. Starting from latest block.")
                # In a real scenario, you might want to start from a specific deployment block.
                self.state['last_processed_block'] = self.source_connector.get_latest_block_number() - 1
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading state file: {e}. Starting fresh.")
            self.state['last_processed_block'] = self.source_connector.get_latest_block_number() - 1

    def _save_state(self) -> None:
        """Saves the current processed block number to the state file."""
        try:
            with open(STATE_FILE_PATH, 'w') as f:
                json.dump(self.state, f)
        except IOError as e:
            logger.error(f"Could not save state to {STATE_FILE_PATH}: {e}")

    def run(self) -> None:
        """Starts the main event listening loop."""
        logger.info("Starting Cross-Chain Event Listener...")
        try:
            while True:
                self._run_cycle()
                logger.debug(f"Cycle finished. Waiting for {LISTENER_POLL_INTERVAL_SECONDS} seconds.")
                time.sleep(LISTENER_POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received. Saving state and exiting.")
        finally:
            self._save_state()
            logger.info("Listener has been shut down.")

    def _run_cycle(self) -> None:
        """Executes a single polling and processing cycle."""
        try:
            latest_block = self.source_connector.get_latest_block_number()
            start_block = self.state['last_processed_block'] + 1

            if start_block > latest_block:
                logger.debug(f"No new blocks to process. Current head: {latest_block}")
                return

            logger.info(f"Processing blocks from {start_block} to {latest_block}")

            # Process blocks in chunks to avoid overwhelming the RPC node
            for block_num in range(start_block, latest_block + 1, BLOCK_PROCESSING_CHUNK_SIZE):
                from_block = block_num
                to_block = min(block_num + BLOCK_PROCESSING_CHUNK_SIZE - 1, latest_block)

                events = self.bridge_handler.fetch_events(
                    event_name='DepositInitiated',
                    from_block=from_block,
                    to_block=to_block
                )

                for event in events:
                    self.event_handler.process_event(event)
                
                # Update state after each successful chunk
                self.state['last_processed_block'] = to_block
                self._save_state()

        except ConnectionError as e:
            logger.error(f"Connection error during cycle: {e}. Will retry on the next cycle.")
        except Exception as e:
            logger.error(f"An unexpected error occurred in the run cycle: {e}", exc_info=True)


def main():
    """Main function to set up and run the listener."""
    try:
        # 1. Initialize connectors for source and destination chains
        source_connector = BlockchainConnector(SOURCE_CHAIN_RPC_URL, SOURCE_CHAIN_ID)
        dest_connector = BlockchainConnector(DESTINATION_CHAIN_RPC_URL, DESTINATION_CHAIN_ID)

        # 2. Initialize contract and event handlers
        bridge_handler = BridgeContractHandler(
            connector=source_connector,
            contract_address=BRIDGE_CONTRACT_ADDRESS,
            abi=BRIDGE_CONTRACT_ABI
        )
        event_handler = CrossChainEventHandler(destination_connector=dest_connector)

        # 3. Set up and run the main listener service
        listener = EventListener(
            source_connector=source_connector,
            dest_connector=dest_connector,
            bridge_handler=bridge_handler,
            event_handler=event_handler
        )
        listener.run()

    except Exception as e:
        logger.critical(f"Failed to initialize the listener components: {e}", exc_info=True)
        # In a real application, this could trigger an alert.


if __name__ == "__main__":
    main()
