"""
Connecteur de Wallets - MetaMask, WalletConnect, Binance
"""

from typing import Dict, Any, Optional
from web3 import Web3
import os

class WalletConnector:
    """Connecteur pour gérer les connexions wallet"""
    
    def __init__(self):
        self.wallet_address = None
        self.wallet_type = None
        self.web3 = None
        self.private_key = None
        self.binance_client = None
        
        print("🔗 Wallet Connector initialisé")
    
    def connect_web3_wallet(
        self,
        wallet_address: str,
        chain: str = 'ethereum',
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Connecte un wallet Web3 (MetaMask, WalletConnect)"""
        try:
            # RPC URLs par chaîne
            rpc_urls = {
                'ethereum': 'https://eth.llamarpc.com',
                'bsc': 'https://bsc-dataseed.binance.org',
                'polygon': 'https://polygon-rpc.com',
                'base': 'https://mainnet.base.org',
                'arbitrum': 'https://arb1.arbitrum.io/rpc'
            }
            
            rpc_url = rpc_urls.get(chain.lower())
            if not rpc_url:
                return {
                    'success': False,
                    'error': f'Chaîne non supportée: {chain}'
                }
            
            # Connecter à Web3
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not self.web3.is_connected():
                return {
                    'success': False,
                    'error': 'Impossible de se connecter au RPC'
                }
            
            # Valider l'adresse
            if not self.web3.is_address(wallet_address):
                return {
                    'success': False,
                    'error': 'Adresse wallet invalide'
                }
            
            self.wallet_address = self.web3.to_checksum_address(wallet_address)
            self.private_key = private_key
            self.wallet_type = 'web3'
            
            print(f"✅ Wallet connecté: {self.wallet_address[:10]}...")
            
            return {
                'success': True,
                'address': self.wallet_address,
                'chain': chain
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def connect_binance(self, api_key: str, api_secret: str) -> Dict[str, Any]:
        """Connecte à Binance via API"""
        try:
            # Import binance seulement si nécessaire
            from binance.client import Client
            
            self.binance_client = Client(api_key, api_secret)
            
            # Test de connexion
            account = self.binance_client.get_account()
            
            self.wallet_type = 'binance'
            
            print("✅ Binance connecté")
            
            return {
                'success': True,
                'type': 'binance'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_connected(self) -> bool:
        """Vérifie si un wallet est connecté"""
        return bool(self.wallet_address or self.binance_client)
    
    def get_native_balance(self) -> float:
        """Récupère le solde natif (ETH, BNB, etc.)"""
        if not self.web3 or not self.wallet_address:
            return 0.0
        
        try:
            balance_wei = self.web3.eth.get_balance(self.wallet_address)
            balance_eth = self.web3.from_wei(balance_wei, 'ether')
            return float(balance_eth)
        except:
            return 0.0
    
    def get_token_balance(self, token_address: str, decimals: int = 18) -> float:
        """Récupère le solde d'un token ERC20"""
        if not self.web3 or not self.wallet_address:
            return 0.0
        
        try:
            # ABI minimal pour balanceOf
            abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],
                   "name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],
                   "type":"function"}]
            
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address),
                abi=abi
            )
            
            balance_wei = contract.functions.balanceOf(self.wallet_address).call()
            balance = balance_wei / (10 ** decimals)
            return float(balance)
        except:
            return 0.0
    
    def get_balances(self) -> Dict[str, float]:
        """Récupère tous les soldes"""
        balances = {}
        
        if self.web3 and self.wallet_address:
            balances['native'] = self.get_native_balance()
        
        if self.binance_client:
            try:
                account = self.binance_client.get_account()
                for balance in account['balances']:
                    free = float(balance['free'])
                    if free > 0:
                        balances[balance['asset']] = free
            except:
                pass
        
        return balances
    
    def disconnect(self):
        """Déconnecte le wallet"""
        self.wallet_address = None
        self.wallet_type = None
        self.web3 = None
        self.private_key = None
        self.binance_client = None
        print("🔌 Wallet déconnecté")


if __name__ == "__main__":
    # Test
    connector = WalletConnector()
    
    # Test Web3
    result = connector.connect_web3_wallet(
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        chain='ethereum'
    )
    
    print(f"Connexion: {result}")
    
    if result['success']:
        print(f"Solde: {connector.get_native_balance()} ETH")