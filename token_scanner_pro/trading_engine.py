"""
Moteur de Trading Semi-Automatique pour Token Scanner Pro
Système de scoring et génération de recommandations BUY/SELL/HOLD
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import time

@dataclass
class TradingSignal:
    """Représente un signal de trading avec tous les détails"""
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0-100
    score: float  # Score global
    reasons: List[str]  # Raisons de la décision
    entry_price: float
    suggested_stop_loss: float
    suggested_take_profit: float
    risk_reward_ratio: float
    position_size_percentage: float  # % du capital à investir
    timestamp: str
    
    # Détails des sous-scores
    technical_score: float
    fundamental_score: float
    sentiment_score: float
    risk_score: float
    
    # Métriques clés
    rsi_value: float
    fibonacci_position: float
    pump_dump_score: float
    liquidity_score: float
    holder_concentration: float


class TradingEngine:
    """Moteur principal de trading avec scoring avancé"""
    
    def __init__(self):
        self.min_liquidity = 10000  # Liquidité minimale en USD
        self.max_pump_score = 60  # Score pump & dump maximum acceptable
        self.min_confidence = 60  # Confiance minimale pour une recommandation
        
        # Poids des différents facteurs (total = 1.0)
        self.weights = {
            'technical': 0.35,    # RSI, Fibonacci, tendances
            'fundamental': 0.25,  # Liquidité, market cap, holders
            'sentiment': 0.20,    # Twitter, social score
            'risk': 0.20          # Sécurité, pump & dump
        }
        
        print("🤖 Trading Engine initialisé")
        print(f"   Poids - Technical: {self.weights['technical']*100}% | "
              f"Fundamental: {self.weights['fundamental']*100}% | "
              f"Sentiment: {self.weights['sentiment']*100}% | "
              f"Risk: {self.weights['risk']*100}%")
    
    # ==================== ANALYSE PRINCIPALE ====================
    
    def analyze_token(self, token_data: Dict[str, Any]) -> TradingSignal:
        """
        Analyse complète d'un token et génère une recommandation de trading
        
        Args:
            token_data: Données du token depuis scanner_core
            
        Returns:
            TradingSignal avec recommandation et détails
        """
        print(f"\n{'='*80}")
        print(f"🔍 ANALYSE TRADING: {token_data['address'][:10]}... ({token_data['chain'].upper()})")
        print(f"{'='*80}")
        
        # 1. Vérifications préliminaires
        if not self._is_tradeable(token_data):
            return self._create_hold_signal(
                token_data,
                "Token non éligible au trading",
                ["Liquidité insuffisante ou honeypot détecté"]
            )
        
        # 2. Calcul des sous-scores
        technical_score = self._calculate_technical_score(token_data)
        fundamental_score = self._calculate_fundamental_score(token_data)
        sentiment_score = self._calculate_sentiment_score(token_data)
        risk_score = self._calculate_risk_score(token_data)
        
        print(f"\n📊 SOUS-SCORES:")
        print(f"   🔧 Technical:    {technical_score:.1f}/100")
        print(f"   📈 Fundamental:  {fundamental_score:.1f}/100")
        print(f"   💬 Sentiment:    {sentiment_score:.1f}/100")
        print(f"   🛡️ Risk:         {risk_score:.1f}/100")
        
        # 3. Score global pondéré
        global_score = (
            technical_score * self.weights['technical'] +
            fundamental_score * self.weights['fundamental'] +
            sentiment_score * self.weights['sentiment'] +
            risk_score * self.weights['risk']
        )
        
        print(f"\n🎯 SCORE GLOBAL: {global_score:.1f}/100")
        
        # 4. Génération de la recommandation
        action, confidence, reasons = self._generate_recommendation(
            global_score,
            technical_score,
            fundamental_score,
            sentiment_score,
            risk_score,
            token_data
        )
        
        # 5. Calcul des prix cibles (Stop-Loss & Take-Profit)
        entry_price = token_data['market'].get('price_usd', 0)
        stop_loss, take_profit = self._calculate_targets(
            entry_price,
            action,
            token_data
        )
        
        # 6. Taille de position recommandée
        position_size = self._calculate_position_size(confidence, risk_score)
        
        # 7. Ratio Risk/Reward
        risk_reward = self._calculate_risk_reward(entry_price, stop_loss, take_profit)
        
        print(f"\n💡 RECOMMANDATION: {action}")
        print(f"   Confiance: {confidence:.1f}%")
        print(f"   Position recommandée: {position_size:.1f}% du capital")
        print(f"   Risk/Reward: 1:{risk_reward:.2f}")
        
        # 8. Création du signal
        signal = TradingSignal(
            action=action,
            confidence=confidence,
            score=global_score,
            reasons=reasons,
            entry_price=entry_price,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            risk_reward_ratio=risk_reward,
            position_size_percentage=position_size,
            timestamp=datetime.now().isoformat(),
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            sentiment_score=sentiment_score,
            risk_score=risk_score,
            rsi_value=token_data.get('rsi_value', 50),
            fibonacci_position=token_data.get('fibonacci_percentage', 50),
            pump_dump_score=token_data.get('pump_dump_score', 0),
            liquidity_score=self._calculate_liquidity_score(token_data),
            holder_concentration=self._get_holder_concentration(token_data)
        )
        
        print(f"{'='*80}\n")
        
        return signal
    
    # ==================== VÉRIFICATIONS ====================
    
    def _is_tradeable(self, token_data: Dict) -> bool:
        """Vérifie si le token est éligible au trading"""
        market = token_data.get('market', {})
        security = token_data.get('security', {})
        
        # Vérif 1: Liquidité minimale
        liquidity = market.get('liquidity_usd', 0)
        if liquidity < self.min_liquidity:
            print(f"❌ Liquidité insuffisante: ${liquidity:,.0f} < ${self.min_liquidity:,.0f}")
            return False
        
        # Vérif 2: Honeypot
        if security.get('is_honeypot', False):
            print(f"❌ HONEYPOT détecté - Trading impossible")
            return False
        
        # Vérif 3: Pump score trop élevé
        pump_score = token_data.get('pump_dump_score', 0)
        if pump_score > self.max_pump_score:
            print(f"⚠️ Pump score trop élevé: {pump_score}/100 > {self.max_pump_score}/100")
            return False
        
        # Vérif 4: Prix valide
        price = market.get('price_usd', 0)
        if price <= 0:
            print(f"❌ Prix invalide: ${price}")
            return False
        
        print("✅ Token éligible au trading")
        return True
    
    # ==================== CALCUL DES SCORES ====================
    
    def _calculate_technical_score(self, token_data: Dict) -> float:
        """Score technique basé sur RSI, Fibonacci, tendances"""
        score = 0
        max_score = 100
        
        # 1. RSI (40 points)
        rsi = token_data.get('rsi_value', 50)
        if rsi <= 30:  # Survendu - Opportunité d'achat
            score += 40
        elif rsi <= 40:
            score += 30
        elif rsi <= 60:
            score += 20
        elif rsi <= 70:
            score += 10
        else:  # Suracheté - Risque
            score += 0
        
        # 2. Fibonacci (30 points)
        fib_pct = token_data.get('fibonacci_percentage', 50)
        if fib_pct <= 23.6:  # Proche du support
            score += 30
        elif fib_pct <= 38.2:
            score += 25
        elif fib_pct <= 61.8:
            score += 15
        elif fib_pct <= 78.6:
            score += 10
        else:  # Proche de la résistance
            score += 0
        
        # 3. Tendance prix (30 points)
        market = token_data.get('market', {})
        change_24h = market.get('price_change_24h', 0)
        change_1h = market.get('price_change_1h', 0)
        
        # Momentum positif modéré (meilleur)
        if 0 < change_24h <= 20 and change_1h > 0:
            score += 30
        elif 0 < change_24h <= 50:
            score += 20
        elif change_24h > 50:  # Trop de hausse = risque
            score += 5
        elif -20 <= change_24h < 0:  # Petite baisse = opportunité
            score += 15
        else:  # Grosse baisse
            score += 0
        
        return (score / max_score) * 100
    
    def _calculate_fundamental_score(self, token_data: Dict) -> float:
        """Score fondamental basé sur liquidité, market cap, holders"""
        score = 0
        max_score = 100
        
        market = token_data.get('market', {})
        security = token_data.get('security', {})
        
        # 1. Liquidité (40 points)
        liquidity = market.get('liquidity_usd', 0)
        if liquidity >= 1000000:  # >1M
            score += 40
        elif liquidity >= 500000:
            score += 35
        elif liquidity >= 100000:
            score += 30
        elif liquidity >= 50000:
            score += 20
        elif liquidity >= 10000:
            score += 10
        
        # 2. Volume / Liquidité ratio (30 points)
        volume = market.get('volume_24h', 0)
        if liquidity > 0:
            vol_liq_ratio = volume / liquidity
            if 0.5 <= vol_liq_ratio <= 5:  # Ratio sain
                score += 30
            elif 5 < vol_liq_ratio <= 10:
                score += 20
            elif vol_liq_ratio < 0.5:
                score += 15
            else:  # Trop de volume = suspect
                score += 0
        
        # 3. Concentration holders (30 points)
        holder_concentration = self._get_holder_concentration(token_data)
        if holder_concentration < 20:  # Bien distribué
            score += 30
        elif holder_concentration < 30:
            score += 25
        elif holder_concentration < 40:
            score += 15
        elif holder_concentration < 50:
            score += 10
        else:  # Trop concentré
            score += 0
        
        return (score / max_score) * 100
    
    def _calculate_sentiment_score(self, token_data: Dict) -> float:
        """Score sentiment basé sur Twitter et social"""
        score = 0
        max_score = 100
        
        # 1. Score social Twitter (70 points)
        social_score = token_data.get('social_score', 0)
        if social_score >= 70:
            score += 70
        elif social_score >= 50:
            score += 60
        elif social_score >= 30:
            score += 45
        elif social_score >= 10:
            score += 25
        elif social_score > 0:
            score += 10
        
        # 2. Présence Twitter (30 points)
        has_twitter = bool(token_data.get('twitter'))
        if has_twitter:
            twitter_data = token_data.get('twitter_data', {})
            followers = twitter_data.get('followers', 0)
            
            if followers >= 100000:
                score += 30
            elif followers >= 50000:
                score += 25
            elif followers >= 10000:
                score += 20
            elif followers >= 1000:
                score += 15
            else:
                score += 10
        
        return (score / max_score) * 100
    
    def _calculate_risk_score(self, token_data: Dict) -> float:
        """Score de risque (inverse - plus c'est bas, plus c'est risqué)"""
        score = 100  # On part de 100 et on retire des points
        
        security = token_data.get('security', {})
        
        # 1. Pump & Dump score (enlever jusqu'à 40 points)
        pump_score = token_data.get('pump_dump_score', 0)
        score -= min(pump_score * 0.4, 40)
        
        # 2. Risque de sécurité (enlever jusqu'à 30 points)
        risk_score = token_data.get('risk_score', 0)
        score -= min(risk_score * 0.3, 30)
        
        # 3. Flags de sécurité (enlever 5 points par flag)
        if security.get('is_mintable'):
            score -= 5
        if security.get('hidden_owner'):
            score -= 10
        if security.get('owner_change_balance'):
            score -= 10
        if security.get('selfdestruct'):
            score -= 15
        
        # 4. Taxes élevées (enlever jusqu'à 10 points)
        buy_tax = security.get('buy_tax', 0)
        sell_tax = security.get('sell_tax', 0)
        if buy_tax > 10 or sell_tax > 10:
            score -= 10
        elif buy_tax > 5 or sell_tax > 5:
            score -= 5
        
        return max(score, 0)  # Ne pas descendre en dessous de 0
    
    # ==================== GÉNÉRATION RECOMMANDATION ====================
    
    def _generate_recommendation(
        self,
        global_score: float,
        technical_score: float,
        fundamental_score: float,
        sentiment_score: float,
        risk_score: float,
        token_data: Dict
    ) -> Tuple[str, float, List[str]]:
        """
        Génère la recommandation BUY/SELL/HOLD avec confiance et raisons
        
        Returns:
            (action, confidence, reasons)
        """
        reasons = []
        
        # Règle 1: Score global très élevé = BUY
        if global_score >= 75:
            action = "BUY"
            confidence = min(global_score, 95)
            reasons.append(f"✅ Excellents indicateurs globaux (score: {global_score:.1f}/100)")
            
            if technical_score >= 70:
                reasons.append(f"📈 Excellents indicateurs techniques (RSI: {token_data.get('rsi_value', 0):.1f})")
            if fundamental_score >= 70:
                reasons.append(f"💎 Fondamentaux solides (liquidité: ${token_data['market'].get('liquidity_usd', 0):,.0f})")
            if sentiment_score >= 60:
                reasons.append(f"🐦 Bon sentiment social (score: {token_data.get('social_score', 0)}/100)")
            if risk_score >= 70:
                reasons.append(f"🛡️ Risque faible (risk score: {token_data.get('risk_score', 0)}/100)")
        
        # Règle 2: Score global moyen mais technique excellent = BUY prudent
        elif global_score >= 60 and technical_score >= 75:
            action = "BUY"
            confidence = 65 + (global_score - 60)
            reasons.append(f"📊 Bons indicateurs techniques (score: {technical_score:.1f}/100)")
            reasons.append(f"⚠️ Position prudente recommandée")
            
            if token_data.get('rsi_value', 50) <= 35:
                reasons.append(f"💎 RSI survendu ({token_data['rsi_value']:.1f}) - Opportunité d'achat")
        
        # Règle 3: Score global faible ou risque élevé = HOLD
        elif global_score < 50 or risk_score < 40:
            action = "HOLD"
            confidence = 70
            reasons.append(f"⏸️ Indicateurs insuffisants pour un achat (score: {global_score:.1f}/100)")
            
            if risk_score < 40:
                reasons.append(f"🚨 Risque trop élevé (risk score: {risk_score:.1f}/100)")
            if token_data.get('pump_dump_score', 0) > 50:
                reasons.append(f"⚠️ Risque de pump & dump détecté ({token_data['pump_dump_score']}/100)")
            if token_data.get('rsi_value', 50) >= 70:
                reasons.append(f"🔥 RSI suracheté ({token_data['rsi_value']:.1f}) - Attendre correction")
        
        # Règle 4: Entre les deux = HOLD prudent
        else:
            action = "HOLD"
            confidence = 60 + (global_score - 50) / 2
            reasons.append(f"⚖️ Indicateurs mitigés (score: {global_score:.1f}/100)")
            reasons.append(f"📊 Attendre de meilleurs signaux d'entrée")
            
            if technical_score < 50:
                reasons.append(f"⏳ Indicateurs techniques défavorables")
            if fundamental_score < 50:
                reasons.append(f"💧 Liquidité ou fondamentaux insuffisants")
        
        # Règle spéciale: SELL si token déjà analysé et suracheté + pump suspect
        # (Cette logique sera étendue quand on aura le suivi de positions)
        rsi = token_data.get('rsi_value', 50)
        pump_score = token_data.get('pump_dump_score', 0)
        if rsi >= 75 and pump_score >= 60 and action == "BUY":
            action = "HOLD"  # Sécurité: ne pas acheter en zone dangereuse
            confidence = 80
            reasons = [
                f"🚨 Conditions de sortie détectées",
                f"🔥 RSI très suracheté ({rsi:.1f})",
                f"⚠️ Score pump & dump élevé ({pump_score}/100)",
                f"💡 Attendre une correction avant d'entrer"
            ]
        
        return action, confidence, reasons
    
    # ==================== CALCULS CIBLES ====================
    
    def _calculate_targets(
        self,
        entry_price: float,
        action: str,
        token_data: Dict
    ) -> Tuple[float, float]:
        """
        Calcule les prix cibles: Stop-Loss et Take-Profit
        
        Returns:
            (stop_loss, take_profit)
        """
        if entry_price <= 0 or action != "BUY":
            return 0.0, 0.0
        
        # Volatilité basée sur le change 24h
        change_24h = abs(token_data['market'].get('price_change_24h', 10))
        
        # Plus c'est volatil, plus on met des stops larges
        if change_24h > 50:  # Très volatil
            stop_loss_pct = 15
            take_profit_pct = 40
        elif change_24h > 20:  # Modérément volatil
            stop_loss_pct = 10
            take_profit_pct = 25
        else:  # Peu volatil
            stop_loss_pct = 7
            take_profit_pct = 20
        
        # Ajustement selon Fibonacci
        fib_pct = token_data.get('fibonacci_percentage', 50)
        if fib_pct <= 23.6:  # Proche support - moins de risque
            stop_loss_pct *= 0.8
            take_profit_pct *= 1.2
        elif fib_pct >= 78.6:  # Proche résistance - plus de risque
            stop_loss_pct *= 1.3
            take_profit_pct *= 0.9
        
        stop_loss = entry_price * (1 - stop_loss_pct / 100)
        take_profit = entry_price * (1 + take_profit_pct / 100)
        
        return round(stop_loss, 10), round(take_profit, 10)
    
    def _calculate_position_size(self, confidence: float, risk_score: float) -> float:
        """
        Calcule la taille de position recommandée (% du capital)
        Plus la confiance est élevée, plus on peut investir
        """
        base_size = 5  # Taille de base: 5% du capital
        
        # Ajustement selon confiance
        if confidence >= 80:
            size = base_size * 1.5  # 7.5%
        elif confidence >= 70:
            size = base_size * 1.2  # 6%
        elif confidence >= 60:
            size = base_size * 1.0  # 5%
        else:
            size = base_size * 0.5  # 2.5%
        
        # Ajustement selon risque
        if risk_score < 50:
            size *= 0.6  # Réduire de 40%
        elif risk_score < 70:
            size *= 0.8  # Réduire de 20%
        
        return min(size, 10)  # Max 10% du capital par position
    
    def _calculate_risk_reward(
        self,
        entry: float,
        stop_loss: float,
        take_profit: float
    ) -> float:
        """Calcule le ratio Risk/Reward"""
        if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
            return 0.0
        
        risk = entry - stop_loss
        reward = take_profit - entry
        
        if risk <= 0:
            return 0.0
        
        return round(reward / risk, 2)
    
    # ==================== HELPERS ====================
    
    def _calculate_liquidity_score(self, token_data: Dict) -> float:
        """Score de liquidité de 0 à 100"""
        liquidity = token_data['market'].get('liquidity_usd', 0)
        
        if liquidity >= 1000000:
            return 100
        elif liquidity >= 500000:
            return 85
        elif liquidity >= 100000:
            return 70
        elif liquidity >= 50000:
            return 55
        elif liquidity >= 10000:
            return 35
        else:
            return max(liquidity / 10000 * 35, 0)
    
    def _get_holder_concentration(self, token_data: Dict) -> float:
        """Récupère la concentration des top holders (%)"""
        security = token_data.get('security', {})
        top_holders = security.get('top_holders', [])
        
        if not top_holders:
            # Fallback sur creator/owner balance
            creator = security.get('creator_balance', 0)
            owner = security.get('owner_balance', 0)
            return max(creator, owner)
        
        # Somme des top 5 holders
        return sum(h.get('percent', 0) for h in top_holders[:5])
    
    def _create_hold_signal(
        self,
        token_data: Dict,
        main_reason: str,
        reasons: List[str]
    ) -> TradingSignal:
        """Crée un signal HOLD par défaut"""
        return TradingSignal(
            action="HOLD",
            confidence=100,
            score=0,
            reasons=[main_reason] + reasons,
            entry_price=token_data['market'].get('price_usd', 0),
            suggested_stop_loss=0,
            suggested_take_profit=0,
            risk_reward_ratio=0,
            position_size_percentage=0,
            timestamp=datetime.now().isoformat(),
            technical_score=0,
            fundamental_score=0,
            sentiment_score=0,
            risk_score=0,
            rsi_value=token_data.get('rsi_value', 50),
            fibonacci_position=token_data.get('fibonacci_percentage', 50),
            pump_dump_score=token_data.get('pump_dump_score', 0),
            liquidity_score=0,
            holder_concentration=0
        )
    
    def signal_to_dict(self, signal: TradingSignal) -> Dict:
        """Convertit un TradingSignal en dictionnaire pour JSON"""
        return {
            'action': signal.action,
            'confidence': round(signal.confidence, 2),
            'score': round(signal.score, 2),
            'reasons': signal.reasons,
            'entry_price': signal.entry_price,
            'suggested_stop_loss': signal.suggested_stop_loss,
            'suggested_take_profit': signal.suggested_take_profit,
            'risk_reward_ratio': signal.risk_reward_ratio,
            'position_size_percentage': round(signal.position_size_percentage, 2),
            'timestamp': signal.timestamp,
            'technical_score': round(signal.technical_score, 2),
            'fundamental_score': round(signal.fundamental_score, 2),
            'sentiment_score': round(signal.sentiment_score, 2),
            'risk_score': round(signal.risk_score, 2),
            'rsi_value': signal.rsi_value,
            'fibonacci_position': signal.fibonacci_position,
            'pump_dump_score': signal.pump_dump_score,
            'liquidity_score': round(signal.liquidity_score, 2),
            'holder_concentration': round(signal.holder_concentration, 2)
        }


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    # Données de test (simulées)
    test_token = {
        'address': '0x1234567890abcdef',
        'chain': 'ethereum',
        'rsi_value': 35,
        'rsi_signal': 'SURVENDU',
        'fibonacci_percentage': 25,
        'pump_dump_score': 25,
        'risk_score': 35,
        'social_score': 65,
        'twitter': 'https://twitter.com/token',
        'twitter_data': {'followers': 50000},
        'market': {
            'price_usd': 0.00045,
            'price_change_24h': 8.5,
            'price_change_1h': 2.1,
            'liquidity_usd': 250000,
            'volume_24h': 180000,
            'market_cap': 2000000
        },
        'security': {
            'is_honeypot': False,
            'is_mintable': False,
            'hidden_owner': False,
            'owner_change_balance': False,
            'selfdestruct': False,
            'buy_tax': 3,
            'sell_tax': 3,
            'top_holders': [
                {'percent': 8.5},
                {'percent': 6.2},
                {'percent': 4.8},
                {'percent': 3.1},
                {'percent': 2.9}
            ]
        }
    }
    
    # Initialiser et tester
    engine = TradingEngine()
    signal = engine.analyze_token(test_token)
    
    print("\n" + "="*80)
    print("📋 RÉSULTAT FINAL")
    print("="*80)
    print(f"Action: {signal.action}")
    print(f"Confiance: {signal.confidence:.1f}%")
    print(f"Score global: {signal.score:.1f}/100")
    print(f"\nPrix d'entrée: ${signal.entry_price:.8f}")
    print(f"Stop-Loss: ${signal.suggested_stop_loss:.8f} (-{((signal.entry_price - signal.suggested_stop_loss) / signal.entry_price * 100):.1f}%)")
    print(f"Take-Profit: ${signal.suggested_take_profit:.8f} (+{((signal.suggested_take_profit - signal.entry_price) / signal.entry_price * 100):.1f}%)")
    print(f"Risk/Reward: 1:{signal.risk_reward_ratio:.2f}")
    print(f"Position recommandée: {signal.position_size_percentage:.1f}% du capital")
    print(f"\nRaisons:")
    for reason in signal.reasons:
        print(f"  • {reason}")