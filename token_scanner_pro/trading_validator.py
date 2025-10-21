"""
Validation des signaux de trading par Claude API (Anthropic)
Analyse experte IA pour confirmer ou ajuster les recommandations
"""

import os
from typing import Dict, Any, Optional
import json
from datetime import datetime
import anthropic
from trading_engine import TradingSignal

class TradingValidator:
    """Validateur IA utilisant Claude pour analyser les signaux de trading"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le validateur avec l'API Claude
        
        Args:
            api_key: Clé API Anthropic (ou variable d'environnement ANTHROPIC_API_KEY)
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "❌ Clé API Anthropic manquante!\n"
                "   Définissez ANTHROPIC_API_KEY dans vos variables d'environnement\n"
                "   Ou passez api_key='sk-ant-...' au constructeur\n"
                "   Obtenez votre clé sur: https://console.anthropic.com/"
            )
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5-20250929"  # Dernier modèle Sonnet
        
        print("🤖 Trading Validator initialisé avec Claude API")
        print(f"   Modèle: {self.model}")
    
    # ==================== VALIDATION PRINCIPALE ====================
    
    def validate_signal(
        self,
        signal: TradingSignal,
        token_data: Dict[str, Any],
        user_profile: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Valide un signal de trading via Claude API
        
        Args:
            signal: Signal généré par TradingEngine
            token_data: Données complètes du token
            user_profile: Profil de risque de l'utilisateur (optionnel)
            
        Returns:
            Dict avec validation IA et recommandations ajustées
        """
        print(f"\n{'='*80}")
        print(f"🧠 VALIDATION IA CLAUDE")
        print(f"{'='*80}")
        
        # 1. Construire le prompt expert
        prompt = self._build_expert_prompt(signal, token_data, user_profile)
        
        # 2. Appeler Claude API
        try:
            response = self._call_claude_api(prompt)
            
            # 3. Parser la réponse
            validation_result = self._parse_claude_response(response, signal)
            
            print(f"\n✅ Validation IA terminée")
            print(f"   Décision finale: {validation_result['final_action']}")
            print(f"   Confiance ajustée: {validation_result['adjusted_confidence']:.1f}%")
            
            return validation_result
            
        except Exception as e:
            print(f"\n❌ Erreur validation IA: {e}")
            
            # En cas d'erreur, retourner le signal original
            return {
                'validation_status': 'error',
                'validation_error': str(e),
                'final_action': signal.action,
                'adjusted_confidence': signal.confidence,
                'ai_analysis': None,
                'ai_warnings': ['Validation IA indisponible - Signal original conservé'],
                'original_signal': signal
            }
    
    # ==================== CONSTRUCTION DU PROMPT ====================
    
    def _build_expert_prompt(
        self,
        signal: TradingSignal,
        token_data: Dict,
        user_profile: Optional[Dict]
    ) -> str:
        """Construit un prompt expert pour Claude"""
        
        # Profil utilisateur par défaut
        risk_tolerance = "modéré"
        capital = "moyen"
        experience = "intermédiaire"
        
        if user_profile:
            risk_tolerance = user_profile.get('risk_tolerance', 'modéré')
            capital = user_profile.get('capital_size', 'moyen')
            experience = user_profile.get('experience', 'intermédiaire')
        
        # Données du token formatées
        market = token_data.get('market', {})
        security = token_data.get('security', {})
        
        prompt = f"""Tu es un expert trader crypto avec 10+ ans d'expérience en analyse technique et fondamentale. Ton rôle est de valider et ajuster une recommandation de trading générée automatiquement.

# PROFIL INVESTISSEUR
- Tolérance au risque: {risk_tolerance}
- Capital: {capital}
- Expérience: {experience}

# DONNÉES DU TOKEN
Adresse: {token_data['address'][:20]}...
Blockchain: {token_data['chain'].upper()}

## Métriques de Marché
- Prix: ${market.get('price_usd', 0):.8f}
- Variation 24h: {market.get('price_change_24h', 0):.2f}%
- Variation 1h: {market.get('price_change_1h', 0):.2f}%
- Liquidité: ${market.get('liquidity_usd', 0):,.0f}
- Volume 24h: ${market.get('volume_24h', 0):,.0f}
- Market Cap: ${market.get('market_cap', 0):,.0f}
- Ratio Vol/Liq: {(market.get('volume_24h', 0) / max(market.get('liquidity_usd', 1), 1)):.2f}

## Indicateurs Techniques
- RSI: {signal.rsi_value:.1f} ({token_data.get('rsi_signal', 'N/A')})
- Position Fibonacci: {signal.fibonacci_position:.1f}%
- Interprétation RSI: {token_data.get('rsi_interpretation', 'N/A')}

## Scores d'Analyse
- Score Technique: {signal.technical_score:.1f}/100
- Score Fondamental: {signal.fundamental_score:.1f}/100
- Score Sentiment: {signal.sentiment_score:.1f}/100
- Score Risque: {signal.risk_score:.1f}/100
- **Score Global: {signal.score:.1f}/100**

## Pump & Dump Detection
- Score Pump & Dump: {signal.pump_dump_score}/100
- Risque: {token_data.get('pump_dump_risk', 'UNKNOWN')}
{self._format_pump_warnings(token_data)}

## Sécurité du Token
- Honeypot: {'⚠️ OUI' if security.get('is_honeypot') else '✅ NON'}
- Code vérifié: {'✅ OUI' if security.get('is_open_source') else '⚠️ NON'}
- Mintable: {'⚠️ OUI' if security.get('is_mintable') else '✅ NON'}
- Owner caché: {'⚠️ OUI' if security.get('hidden_owner') else '✅ NON'}
- Tax Achat/Vente: {security.get('buy_tax', 0)}% / {security.get('sell_tax', 0)}%
- Holders: {security.get('holder_count', 'N/A')}
- Concentration Top 5: {signal.holder_concentration:.1f}%

## Score Social (Twitter)
- Score global: {token_data.get('social_score', 0)}/100
{self._format_twitter_data(token_data)}

## Âge du Token
{self._format_token_age(token_data)}

# RECOMMANDATION AUTOMATIQUE
**Action proposée: {signal.action}**
**Confiance: {signal.confidence:.1f}%**

Position suggérée: {signal.position_size_percentage:.1f}% du capital
Entry: ${signal.entry_price:.8f}
Stop-Loss: ${signal.suggested_stop_loss:.8f} ({self._calculate_sl_percentage(signal)}%)
Take-Profit: ${signal.suggested_take_profit:.8f} ({self._calculate_tp_percentage(signal)}%)
Risk/Reward: 1:{signal.risk_reward_ratio:.2f}

**Raisons de la recommandation:**
{self._format_reasons(signal.reasons)}

# TA MISSION
Analyse en profondeur cette recommandation et réponds AU FORMAT JSON suivant:

```json
{{
  "validation_status": "approved|adjusted|rejected",
  "final_action": "BUY|SELL|HOLD",
  "adjusted_confidence": 0-100,
  "confidence_change_reason": "Explication du changement de confiance",
  "ai_analysis": {{
    "technical_assessment": "Ton analyse des indicateurs techniques",
    "risk_assessment": "Ton évaluation du risque",
    "market_context": "Contexte de marché et timing",
    "key_concerns": ["Liste des préoccupations majeures"],
    "key_strengths": ["Liste des points forts"]
  }},
  "adjusted_targets": {{
    "stop_loss": 0.0,
    "take_profit": 0.0,
    "position_size": 0.0
  }},
  "warnings": ["Avertissements spécifiques pour l'utilisateur"],
  "recommendations": ["Recommandations additionnelles"],
  "overall_verdict": "Résumé court (2-3 phrases) de ta décision finale"
}}
```

**IMPORTANT:**
1. Sois TRÈS strict sur les red flags (honeypot, pump suspect, liquidité faible)
2. Ajuste la confiance à la BAISSE si tu détectes des risques que le système automatique a sous-estimés
3. Un HOLD est souvent la meilleure décision face au doute
4. Pour un trader {experience} avec tolérance {risk_tolerance}, privilégie la PRUDENCE
5. Réponds UNIQUEMENT avec le JSON, rien d'autre"""

        return prompt
    
    # ==================== APPEL API CLAUDE ====================
    
    def _call_claude_api(self, prompt: str) -> str:
        """Appelle l'API Claude et retourne la réponse"""
        print("\n🔄 Envoi à Claude API...")
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Faible pour plus de cohérence
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text
            print("✅ Réponse reçue de Claude")
            
            return response_text
            
        except anthropic.APIError as e:
            print(f"❌ Erreur API Anthropic: {e}")
            raise
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            raise
    
    # ==================== PARSING DE LA RÉPONSE ====================
    
    def _parse_claude_response(
        self,
        response: str,
        original_signal: TradingSignal
    ) -> Dict[str, Any]:
        """Parse la réponse JSON de Claude"""
        
        try:
            # Extraire le JSON de la réponse (peut être dans des code blocks)
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            # Parser le JSON
            validation = json.loads(json_str.strip())
            
            # Vérifier les champs requis
            required_fields = ['validation_status', 'final_action', 'adjusted_confidence']
            for field in required_fields:
                if field not in validation:
                    raise ValueError(f"Champ requis manquant: {field}")
            
            # Construire le résultat complet
            result = {
                'validation_status': validation['validation_status'],
                'final_action': validation['final_action'],
                'adjusted_confidence': float(validation['adjusted_confidence']),
                'confidence_change': validation.get('confidence_change_reason', ''),
                'ai_analysis': validation.get('ai_analysis', {}),
                'adjusted_targets': validation.get('adjusted_targets', {
                    'stop_loss': original_signal.suggested_stop_loss,
                    'take_profit': original_signal.suggested_take_profit,
                    'position_size': original_signal.position_size_percentage
                }),
                'ai_warnings': validation.get('warnings', []),
                'ai_recommendations': validation.get('recommendations', []),
                'overall_verdict': validation.get('overall_verdict', ''),
                'original_signal': original_signal,
                'validation_timestamp': datetime.now().isoformat(),
                'model_used': self.model
            }
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {e}")
            print(f"Réponse brute: {response[:500]}...")
            raise ValueError(f"Impossible de parser la réponse JSON de Claude: {e}")
        
        except Exception as e:
            print(f"❌ Erreur parsing: {e}")
            raise
    
    # ==================== HELPERS FORMATAGE ====================
    
    def _format_pump_warnings(self, token_data: Dict) -> str:
        """Formate les warnings pump & dump"""
        warnings = token_data.get('pump_dump_warnings', [])
        if not warnings:
            return "- Aucun warning détecté"
        
        formatted = "\nWarnings détectés:\n"
        for warning in warnings[:5]:  # Max 5
            formatted += f"  ⚠️ {warning}\n"
        return formatted
    
    def _format_twitter_data(self, token_data: Dict) -> str:
        """Formate les données Twitter"""
        twitter_data = token_data.get('twitter_data', {})
        social_details = token_data.get('social_details', {})
        
        if not twitter_data:
            return "- Pas de Twitter"
        
        return f"""- Followers: {twitter_data.get('followers', 0):,}
- Following: {twitter_data.get('following', 0):,}
- Tweets: {twitter_data.get('tweets', 0):,}
- Vérifié: {social_details.get('verified', 'Non')}
- Ratio F/F: {social_details.get('ratio_score', 'N/A')}"""
    
    def _format_token_age(self, token_data: Dict) -> str:
        """Formate l'âge du token"""
        age = token_data.get('token_age_hours', 'N/A')
        if age == 'N/A':
            return "- Âge: Inconnu"
        
        if age < 24:
            return f"- Âge: {age:.1f}h (⚠️ TRÈS RÉCENT)"
        elif age < 72:
            return f"- Âge: {age/24:.1f} jours (RÉCENT)"
        else:
            return f"- Âge: {age/24:.1f} jours"
    
    def _format_reasons(self, reasons: list) -> str:
        """Formate les raisons"""
        return "\n".join(f"  • {reason}" for reason in reasons)
    
    def _calculate_sl_percentage(self, signal: TradingSignal) -> str:
        """Calcule le % du Stop-Loss"""
        if signal.entry_price <= 0 or signal.suggested_stop_loss <= 0:
            return "0.0"
        pct = ((signal.entry_price - signal.suggested_stop_loss) / signal.entry_price) * 100
        return f"-{pct:.1f}"
    
    def _calculate_tp_percentage(self, signal: TradingSignal) -> str:
        """Calcule le % du Take-Profit"""
        if signal.entry_price <= 0 or signal.suggested_take_profit <= 0:
            return "0.0"
        pct = ((signal.suggested_take_profit - signal.entry_price) / signal.entry_price) * 100
        return f"+{pct:.1f}"
    
    # ==================== MÉTHODES UTILITAIRES ====================
    
    def should_execute_trade(self, validation_result: Dict) -> bool:
        """
        Détermine si le trade doit être exécuté selon la validation IA
        
        Returns:
            True si BUY approuvé avec confiance > 60%
        """
        if validation_result['validation_status'] == 'error':
            return False
        
        action = validation_result['final_action']
        confidence = validation_result['adjusted_confidence']
        
        # Seuil de confiance minimum
        MIN_CONFIDENCE = 60
        
        return action == 'BUY' and confidence >= MIN_CONFIDENCE
    
    def get_execution_summary(self, validation_result: Dict) -> str:
        """Génère un résumé pour l'utilisateur"""
        action = validation_result['final_action']
        confidence = validation_result['adjusted_confidence']
        verdict = validation_result.get('overall_verdict', 'N/A')
        
        emoji = {
            'BUY': '🟢',
            'SELL': '🔴',
            'HOLD': '🟡'
        }.get(action, '⚪')
        
        summary = f"""
{emoji} DÉCISION FINALE: {action}
Confiance: {confidence:.1f}%

{verdict}

Warnings:
"""
        for warning in validation_result.get('ai_warnings', []):
            summary += f"⚠️ {warning}\n"
        
        summary += "\nRecommandations:\n"
        for rec in validation_result.get('ai_recommendations', []):
            summary += f"💡 {rec}\n"
        
        return summary


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    from trading_engine import TradingEngine, TradingSignal
    
    # IMPORTANT: Définir votre clé API
    # export ANTHROPIC_API_KEY="sk-ant-..."
    # OU:
    # validator = TradingValidator(api_key="sk-ant-...")
    
    print("="*80)
    print("TEST TRADING VALIDATOR")
    print("="*80)
    
    # Données de test
    test_token = {
        'address': '0x1234567890abcdef1234567890abcdef12345678',
        'chain': 'ethereum',
        'rsi_value': 35,
        'rsi_signal': 'SURVENDU',
        'rsi_interpretation': 'Potentiel rebond technique',
        'fibonacci_percentage': 25,
        'fibonacci_position': 'Près du support',
        'pump_dump_score': 25,
        'pump_dump_risk': 'LOW',
        'pump_dump_warnings': [],
        'risk_score': 35,
        'social_score': 65,
        'twitter': 'https://twitter.com/token',
        'twitter_data': {
            'followers': 50000,
            'following': 500,
            'tweets': 1200,
        },
        'social_details': {
            'verified': 'Non',
            'ratio_score': 'Excellent (100:1)'
        },
        'token_age_hours': 168,  # 7 jours
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
            'is_open_source': True,
            'is_mintable': False,
            'hidden_owner': False,
            'owner_change_balance': False,
            'selfdestruct': False,
            'buy_tax': 3,
            'sell_tax': 3,
            'holder_count': 1250,
            'top_holders': [
                {'percent': 8.5},
                {'percent': 6.2},
                {'percent': 4.8},
                {'percent': 3.1},
                {'percent': 2.9}
            ]
        }
    }
    
    # Créer un signal de test
    test_signal = TradingSignal(
        action="BUY",
        confidence=78.5,
        score=75.3,
        reasons=[
            "✅ Excellents indicateurs globaux (score: 75.3/100)",
            "📈 Excellents indicateurs techniques (RSI: 35.0)",
            "💎 Fondamentaux solides (liquidité: $250,000)"
        ],
        entry_price=0.00045,
        suggested_stop_loss=0.000405,
        suggested_take_profit=0.000563,
        risk_reward_ratio=2.5,
        position_size_percentage=7.5,
        timestamp=datetime.now().isoformat(),
        technical_score=82.0,
        fundamental_score=75.0,
        sentiment_score=65.0,
        risk_score=78.0,
        rsi_value=35.0,
        fibonacci_position=25.0,
        pump_dump_score=25,
        liquidity_score=85.0,
        holder_concentration=25.5
    )
    
    try:
        # Initialiser le validateur
        validator = TradingValidator()
        
        # Profil utilisateur
        user_profile = {
            'risk_tolerance': 'modéré',
            'capital_size': 'moyen',
            'experience': 'intermédiaire'
        }
        
        # Valider le signal
        result = validator.validate_signal(test_signal, test_token, user_profile)
        
        # Afficher le résultat
        print("\n" + "="*80)
        print("RÉSULTAT DE LA VALIDATION")
        print("="*80)
        print(validator.get_execution_summary(result))
        
        print("\n" + "="*80)
        print(f"Exécution recommandée: {validator.should_execute_trade(result)}")
        print("="*80)
        
    except ValueError as e:
        print(f"\n{e}")
        print("\nPour tester ce module, définissez votre clé API Anthropic:")
        print("export ANTHROPIC_API_KEY='sk-ant-...'")