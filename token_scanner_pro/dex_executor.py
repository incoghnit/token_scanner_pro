"""
Exécuteur de trades sur DEX (Decentralized Exchanges)
Support: Uniswap V3, PancakeSwap V3, et autres DEX compatibles
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from web3 import Web3
from eth_account import Account
import json
import time
from datetime import datetime

class DEXConfig:
    """Configuration des DEX supportés"""
    
    # Routers principaux par chaîne
    ROUTERS = {
        'ethereum': {
            'uniswap_v3': {
                'router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',  # SwapRouter
                'quoter': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',  # QuoterV2
                'factory': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
                'name': 'Uniswap V3'
            }
        },
        'bsc': {
            'pancakeswap_v3': {
                'router': '0x1b81D678ffb9C0263b24A97847620C99d213eB14',  # PancakeSwap V3 Router
                'quoter': '0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997',
                'factory': '0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865',
                'name': 'PancakeSwap V3'
            }
        },
        'polygon': {
            'uniswap_v3': {
                'router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
                'quoter': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
                'factory': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
                'name': 'Uniswap V3'
            }
        },
        'base': {
            'uniswap_v3': {
                'router': '0x2626664c2603336E57B271c5C0b26F421741e481',  # Universal Router Base
                'quoter': '0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a',
                'factory': '0x33128a8fC17869897dcE68Ed026d694621f6FDfD',
                'name': 'Uniswap V3'
            }
        },
        'arbitrum': {
            'uniswap_v3': {
                'router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
                'quoter': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
                'factory': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
                'name': 'Uniswap V3'
            }
        }
    }
    
    # Frais de pool standards (en basis points)
    FEE_TIERS = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
    
    @classmethod
    def get_router(cls, chain: str, dex: str = 'auto') -> Optional[Dict]:
        """Récupère la config d'un router"""
        chain_lower = chain.lower()
        
        if chain_lower not in cls.ROUTERS:
            return None
        
        if dex == 'auto':
            # Retourner le premier DEX disponible
            return next(iter(cls.ROUTERS[chain_lower].values()))
        
        return cls.ROUTERS[chain_lower].get(dex)


class DEXExecutor:
    """Exécuteur principal de trades sur DEX"""
    
    def __init__(self, wallet_connector):
        """
        Initialise l'exécuteur DEX
        
        Args:
            wallet_connector: Instance de WalletConnector
        """
        self.wallet = wallet_connector
        self.web3 = None
        self.chain = None
        self.router_config = None
        
        # ABIs minimaux
        self._load_abis()
        
        print("🔀 DEX Executor initialisé")
    
    def _load_abis(self):
        """Charge les ABIs nécessaires"""
        # ABI ERC20 minimal
        self.erc20_abi = json.loads('''[
            {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
            {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
            {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},
            {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
        ]''')
        
        # ABI Uniswap V3 SwapRouter (fonction exactInputSingle)
        self.swap_router_abi = json.loads('''[
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            }
        ]''')
        
        # ABI Quoter V2 (pour estimer les swaps)
        self.quoter_abi = json.loads('''[
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct IQuoterV2.QuoteExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "quoteExactInputSingle",
                "outputs": [
                    {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
                    {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
                    {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
                ],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]''')
    
    # ==================== INITIALISATION ====================
    
    def initialize(self, chain: str, dex: str = 'auto') -> bool:
        """
        Initialise l'exécuteur pour une chaîne et un DEX
        
        Args:
            chain: Chaîne (ethereum, bsc, etc.)
            dex: DEX à utiliser ('auto' pour automatique)
            
        Returns:
            True si succès
        """
        print(f"\n{'='*80}")
        print(f"🔀 INITIALISATION DEX EXECUTOR")
        print(f"{'='*80}")
        
        try:
            # 1. Vérifier que le wallet est connecté
            if not self.wallet.is_connected():
                raise ConnectionError("Wallet non connecté")
            
            if not self.wallet.web3:
                raise ConnectionError("Wallet Web3 non initialisé")
            
            # 2. Récupérer la config du router
            self.router_config = DEXConfig.get_router(chain, dex)
            
            if not self.router_config:
                raise ValueError(f"DEX non supporté pour la chaîne {chain}")
            
            print(f"✅ DEX sélectionné: {self.router_config['name']}")
            print(f"   Router: {self.router_config['router']}")
            
            # 3. Stocker les infos
            self.web3 = self.wallet.web3
            self.chain = chain
            
            print(f"✅ DEX Executor prêt pour {chain}")
            print(f"{'='*80}\n")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur initialisation: {e}")
            return False
    
    # ==================== APPROBATION (APPROVE) ====================
    
    def approve_token(
        self,
        token_address: str,
        amount: Optional[float] = None,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approuve le router à utiliser des tokens
        
        Args:
            token_address: Adresse du token à approuver
            amount: Montant à approuver (None = infinite)
            private_key: Clé privée pour signer
            
        Returns:
            Dict avec tx hash et status
        """
        print(f"\n{'='*80}")
        print(f"✅ APPROBATION TOKEN")
        print(f"{'='*80}")
        
        try:
            if not self.router_config:
                raise ValueError("DEX non initialisé")
            
            # 1. Créer le contrat token
            token_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address),
                abi=self.erc20_abi
            )
            
            # 2. Récupérer les décimales
            decimals = token_contract.functions.decimals().call()
            
            # 3. Calculer le montant à approuver
            if amount is None:
                # Infinite approval (2^256 - 1)
                amount_wei = 2**256 - 1
                print("🔓 Approbation infinie")
            else:
                amount_wei = int(amount * (10 ** decimals))
                print(f"🔓 Approbation: {amount:.6f} tokens")
            
            # 4. Vérifier l'allowance actuelle
            current_allowance = token_contract.functions.allowance(
                self.wallet.wallet_address,
                self.router_config['router']
            ).call()
            
            if current_allowance >= amount_wei:
                print("✅ Allowance déjà suffisante")
                return {
                    'success': True,
                    'already_approved': True,
                    'allowance': current_allowance / (10 ** decimals)
                }
            
            print(f"📝 Construction de la transaction approve...")
            
            # 5. Construire la transaction
            approve_tx = token_contract.functions.approve(
                self.router_config['router'],
                amount_wei
            ).build_transaction({
                'from': self.wallet.wallet_address,
                'nonce': self.web3.eth.get_transaction_count(self.wallet.wallet_address),
                'gas': 100000,  # Gas fixe pour approve
                'gasPrice': self.web3.eth.gas_price
            })
            
            # 6. Signer et envoyer
            if not private_key:
                raise ValueError("Clé privée requise pour signer la transaction")
            
            signed_tx = self.web3.eth.account.sign_transaction(approve_tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            print(f"📤 Transaction envoyée: {tx_hash.hex()}")
            print(f"⏳ Attente de confirmation...")
            
            # 7. Attendre la confirmation
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if tx_receipt['status'] == 1:
                print(f"✅ Approbation confirmée!")
                print(f"{'='*80}\n")
                
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'gas_used': tx_receipt['gasUsed'],
                    'approved_amount': amount if amount else 'infinite'
                }
            else:
                raise Exception("Transaction échouée")
                
        except Exception as e:
            print(f"❌ Erreur approbation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== ESTIMATION DE SWAP ====================
    
    def estimate_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        fee_tier: int = 3000
    ) -> Optional[Dict[str, Any]]:
        """
        Estime un swap sans l'exécuter
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            amount_in: Montant à échanger
            fee_tier: Frais du pool (100, 500, 3000, 10000)
            
        Returns:
            Dict avec estimation ou None
        """
        try:
            if not self.router_config:
                raise ValueError("DEX non initialisé")
            
            print(f"\n📊 Estimation du swap...")
            
            # 1. Obtenir les décimales du token in
            token_in_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_in),
                abi=self.erc20_abi
            )
            decimals_in = token_in_contract.functions.decimals().call()
            
            # 2. Obtenir les décimales du token out
            token_out_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_out),
                abi=self.erc20_abi
            )
            decimals_out = token_out_contract.functions.decimals().call()
            
            # 3. Convertir le montant
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            
            # 4. Créer le contrat quoter
            quoter_contract = self.web3.eth.contract(
                address=self.router_config['quoter'],
                abi=self.quoter_abi
            )
            
            # 5. Appeler quoteExactInputSingle
            quote_params = (
                self.web3.to_checksum_address(token_in),
                self.web3.to_checksum_address(token_out),
                amount_in_wei,
                fee_tier,
                0  # sqrtPriceLimitX96 (0 = pas de limite)
            )
            
            result = quoter_contract.functions.quoteExactInputSingle(quote_params).call()
            
            # 6. Parser le résultat
            amount_out_wei = result[0]
            gas_estimate = result[3]
            
            amount_out = amount_out_wei / (10 ** decimals_out)
            
            # 7. Calculer le prix
            price = amount_out / amount_in if amount_in > 0 else 0
            
            print(f"✅ Estimation:")
            print(f"   In:  {amount_in:.6f} tokens")
            print(f"   Out: {amount_out:.6f} tokens")
            print(f"   Prix: {price:.8f}")
            print(f"   Gas estimé: {gas_estimate}")
            
            return {
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price': price,
                'gas_estimate': int(gas_estimate),
                'fee_tier': fee_tier
            }
            
        except Exception as e:
            print(f"❌ Erreur estimation: {e}")
            return None
    
    # ==================== EXÉCUTION DE SWAP ====================
    
    def execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        slippage_tolerance: float = 1.0,
        fee_tier: int = 3000,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exécute un swap sur le DEX
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            amount_in: Montant à échanger
            slippage_tolerance: Tolérance au slippage (%)
            fee_tier: Frais du pool (100, 500, 3000, 10000)
            private_key: Clé privée pour signer
            
        Returns:
            Dict avec résultat du swap
        """
        print(f"\n{'='*80}")
        print(f"💱 EXÉCUTION SWAP")
        print(f"{'='*80}")
        
        try:
            if not self.router_config:
                raise ValueError("DEX non initialisé")
            
            if not private_key:
                raise ValueError("Clé privée requise pour exécuter le swap")
            
            # 1. Estimer le swap
            estimation = self.estimate_swap(token_in, token_out, amount_in, fee_tier)
            
            if not estimation:
                raise Exception("Impossible d'estimer le swap")
            
            # 2. Calculer amountOutMinimum avec slippage
            amount_out_min = estimation['amount_out'] * (1 - slippage_tolerance / 100)
            
            print(f"\n💱 Swap:")
            print(f"   {amount_in:.6f} tokens IN")
            print(f"   {estimation['amount_out']:.6f} tokens OUT (estimé)")
            print(f"   {amount_out_min:.6f} tokens OUT minimum (slippage {slippage_tolerance}%)")
            
            # 3. Vérifier l'approbation
            print(f"\n🔍 Vérification de l'allowance...")
            
            token_in_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_in),
                abi=self.erc20_abi
            )
            
            decimals_in = token_in_contract.functions.decimals().call()
            decimals_out = token_in_contract.functions.decimals().call()
            
            allowance = token_in_contract.functions.allowance(
                self.wallet.wallet_address,
                self.router_config['router']
            ).call()
            
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            
            if allowance < amount_in_wei:
                print(f"⚠️ Allowance insuffisante, approbation requise...")
                approve_result = self.approve_token(token_in, amount_in * 1.5, private_key)
                
                if not approve_result['success']:
                    raise Exception("Échec de l'approbation")
                
                time.sleep(5)  # Attendre confirmation
            
            # 4. Construire les paramètres du swap
            deadline = int(time.time()) + 300  # 5 minutes
            amount_out_min_wei = int(amount_out_min * (10 ** decimals_out))
            
            swap_params = (
                self.web3.to_checksum_address(token_in),      # tokenIn
                self.web3.to_checksum_address(token_out),     # tokenOut
                fee_tier,                                      # fee
                self.wallet.wallet_address,                   # recipient
                deadline,                                      # deadline
                amount_in_wei,                                # amountIn
                amount_out_min_wei,                           # amountOutMinimum
                0                                              # sqrtPriceLimitX96
            )
            
            # 5. Créer le contrat router
            router_contract = self.web3.eth.contract(
                address=self.router_config['router'],
                abi=self.swap_router_abi
            )
            
            # 6. Estimer le gas
            print(f"\n⛽ Estimation du gas...")
            
            gas_estimate = router_contract.functions.exactInputSingle(
                swap_params
            ).estimate_gas({
                'from': self.wallet.wallet_address,
                'value': 0
            })
            
            gas_limit = int(gas_estimate * 1.2)  # +20% de marge
            
            print(f"   Gas estimé: {gas_estimate}")
            print(f"   Gas limit: {gas_limit}")
            
            # 7. Construire la transaction
            print(f"\n📝 Construction de la transaction...")
            
            swap_tx = router_contract.functions.exactInputSingle(
                swap_params
            ).build_transaction({
                'from': self.wallet.wallet_address,
                'nonce': self.web3.eth.get_transaction_count(self.wallet.wallet_address),
                'gas': gas_limit,
                'gasPrice': self.web3.eth.gas_price,
                'value': 0
            })
            
            # 8. Signer et envoyer
            print(f"🔐 Signature de la transaction...")
            
            signed_tx = self.web3.eth.account.sign_transaction(swap_tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            print(f"📤 Transaction envoyée: {tx_hash.hex()}")
            print(f"⏳ Attente de confirmation...")
            
            # 9. Attendre la confirmation
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if tx_receipt['status'] == 1:
                # 10. Calculer le montant réel reçu
                # (en production, parser les logs pour obtenir le montant exact)
                
                gas_used = tx_receipt['gasUsed']
                gas_price = swap_tx['gasPrice']
                gas_cost_eth = self.web3.from_wei(gas_used * gas_price, 'ether')
                
                print(f"\n✅ SWAP RÉUSSI!")
                print(f"   TX Hash: {tx_hash.hex()}")
                print(f"   Gas utilisé: {gas_used}")
                print(f"   Coût gas: {gas_cost_eth:.6f} ETH")
                print(f"{'='*80}\n")
                
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'amount_in': amount_in,
                    'amount_out_expected': estimation['amount_out'],
                    'amount_out_minimum': amount_out_min,
                    'gas_used': gas_used,
                    'gas_cost_eth': float(gas_cost_eth),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                raise Exception("Transaction échouée")
                
        except Exception as e:
            print(f"\n❌ ERREUR SWAP: {e}")
            print(f"{'='*80}\n")
            
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== HELPERS ====================
    
    def find_best_fee_tier(
        self,
        token_in: str,
        token_out: str,
        amount_in: float
    ) -> int:
        """
        Trouve le meilleur fee tier (pool avec meilleure liquidité)
        
        Args:
            token_in: Token d'entrée
            token_out: Token de sortie
            amount_in: Montant
            
        Returns:
            Fee tier optimal (100, 500, 3000, 10000)
        """
        print(f"\n🔍 Recherche du meilleur pool...")
        
        best_fee = 3000  # Défaut
        best_amount_out = 0
        
        for fee in DEXConfig.FEE_TIERS:
            try:
                estimate = self.estimate_swap(token_in, token_out, amount_in, fee)
                
                if estimate and estimate['amount_out'] > best_amount_out:
                    best_amount_out = estimate['amount_out']
                    best_fee = fee
                    
                print(f"   Fee {fee/10000:.2f}%: {estimate['amount_out']:.6f} tokens")
            except:
                pass
        
        print(f"✅ Meilleur pool: {best_fee/10000:.2f}%")
        
        return best_fee


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    from wallet_connector import WalletConnector
    
    print("="*80)
    print("TEST DEX EXECUTOR")
    print("="*80)
    
    # ATTENTION: Ceci est un test sur MAINNET réel
    # Utilisez un wallet de test avec peu de fonds!
    
    print("\n⚠️ AVERTISSEMENT:")
    print("   Ce test utilise de vraies transactions sur mainnet")
    print("   Assurez-vous d'utiliser un wallet de test!")
    
    # 1. Connecter un wallet
    connector = WalletConnector()
    
    # Remplacer par votre adresse et clé privée de TEST
    TEST_ADDRESS = os.environ.get('TEST_WALLET_ADDRESS', '0x...')
    TEST_PRIVATE_KEY = os.environ.get('TEST_PRIVATE_KEY', '0x...')
    
    if TEST_ADDRESS == '0x...' or TEST_PRIVATE_KEY == '0x...':
        print("\n⏭️ Test skipped - Définissez TEST_WALLET_ADDRESS et TEST_PRIVATE_KEY")
        exit()
    
    result = connector.connect_web3_wallet(
        wallet_address=TEST_ADDRESS,
        chain='ethereum',
        private_key=TEST_PRIVATE_KEY
    )
    
    if not result['success']:
        print("❌ Échec connexion wallet")
        exit()
    
    # 2. Initialiser le DEX executor
    executor = DEXExecutor(connector)
    
    if not executor.initialize('ethereum'):
        print("❌ Échec initialisation DEX")
        exit()
    
    # 3. Tester l'estimation (USDC -> DAI sur Ethereum)
    USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    
    print("\n3️⃣ TEST ESTIMATION SWAP")
    estimation = executor.estimate_swap(
        token_in=USDC,
        token_out=DAI,
        amount_in=10,  # 10 USDC
        fee_tier=3000  # 0.3%
    )
    
    if estimation:
        print(f"\n✅ Estimation réussie")
        print(f"   10 USDC → {estimation['amount_out']:.2f} DAI")
    
    # 4. Tester un swap RÉEL (décommentez si vous voulez vraiment échanger)
    # print("\n4️⃣ TEST SWAP RÉEL")
    # swap_result = executor.execute_swap(
    #     token_in=USDC,
    #     token_out=DAI,
    #     amount_in=1,  # 1 USDC
    #     slippage_tolerance=2.0,
    #     fee_tier=3000,
    #     private_key=TEST_PRIVATE_KEY
    # )
    
    print("\n" + "="*80)
    print("TESTS TERMINÉS")
    print("="*80)