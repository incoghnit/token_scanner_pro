"""
Système d'alertes pour utilisateurs Premium
Version améliorée avec RSI, Fibonacci et détection adaptée aux nouveaux tokens
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import Database
from scanner_core import TokenScanner

class AlertSystem:
    def __init__(self, 
                 smtp_server: str = "smtp.gmail.com",
                 smtp_port: int = 587,
                 smtp_user: str = "",
                 smtp_password: str = ""):
        """
        Initialise le système d'alertes
        
        IMPORTANT: Pour Gmail, utilisez un "App Password" :
        1. Activez la validation en 2 étapes
        2. Générez un mot de passe d'application sur https://myaccount.google.com/apppasswords
        """
        self.db = Database()
        self.scanner = TokenScanner()
        
        # Configuration SMTP
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        
        # Surveillance active
        self.monitoring = False
        self.check_interval = 3600  # 1 heure en secondes
        
        print("🚨 Système d'alertes initialisé (RSI + Fibonacci)")
    
    def start_monitoring(self):
        """Démarre la surveillance automatique des favoris"""
        if self.monitoring:
            print("⚠️ Surveillance déjà active")
            return
        
        self.monitoring = True
        thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        thread.start()
        print("✅ Surveillance automatique démarrée (vérification toutes les heures)")
    
    def stop_monitoring(self):
        """Arrête la surveillance automatique"""
        self.monitoring = False
        print("🛑 Surveillance automatique arrêtée")
    
    def _monitoring_loop(self):
        """Boucle principale de surveillance"""
        while self.monitoring:
            try:
                print(f"\n🔍 [{datetime.now().strftime('%H:%M:%S')}] Vérification des favoris premium...")
                self.check_all_premium_favorites()
                print(f"✅ Vérification terminée. Prochaine vérification dans {self.check_interval//60} minutes.\n")
            except Exception as e:
                print(f"❌ Erreur lors de la vérification: {e}")
            
            time.sleep(self.check_interval)
    
    def check_all_premium_favorites(self):
        """Vérifie les favoris de tous les utilisateurs premium"""
        all_users = self.db.get_all_users()
        premium_users = [u for u in all_users if u.get('is_premium')]
        
        print(f"📊 {len(premium_users)} utilisateur(s) premium à vérifier")
        
        for user in premium_users:
            try:
                self._check_user_favorites(user)
            except Exception as e:
                print(f"❌ Erreur pour l'utilisateur {user['username']}: {e}")
    
    def _check_user_favorites(self, user: Dict):
        """Vérifie les favoris d'un utilisateur spécifique"""
        user_id = user['id']
        username = user['username']
        email = user['email']
        
        favorites = self.db.get_user_favorites(user_id)
        
        if not favorites:
            return
        
        print(f"  👤 {username}: {len(favorites)} favori(s)")
        
        alerts = []
        
        for favorite in favorites:
            token_address = favorite['token_address']
            token_chain = favorite['token_chain']
            
            try:
                token_info = {
                    'address': token_address,
                    'chain': token_chain,
                    'url': '',
                    'icon': '',
                    'description': '',
                    'twitter': '',
                    'links': []
                }
                
                current_data = self.scanner.analyze_token(token_info)
                
                # Détecter les changements critiques (avec nouvelles métriques)
                alert = self._detect_critical_changes(favorite, current_data)
                
                if alert:
                    alerts.append(alert)
                    self._save_alert_to_db(user_id, alert)
                
            except Exception as e:
                print(f"    ❌ Erreur analyse {token_address[:8]}...: {e}")
        
        # Envoyer les alertes si il y en a
        if alerts:
            print(f"  🚨 {len(alerts)} alerte(s) détectée(s) pour {username}")
            
            if email:
                self.send_email_alert(email, username, alerts)
            
            for alert in alerts:
                self._create_web_notification(user_id, alert)
    
    def _detect_critical_changes(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """
        🆕 Détecte les changements critiques avec RSI, Fibonacci et pump & dump adapté
        """
        alerts_list = []
        alert_type = "info"
        
        # 🆕 1. ALERTE RSI SURACHETÉ
        if new_data.get('rsi_value', 50) >= 70:
            alert_type = "critical"
            alerts_list.append({
                "type": "rsi_overbought",
                "severity": "critical",
                "message": f"🔥 RSI SURACHETÉ: {new_data['rsi_value']}/100",
                "details": [
                    f"Signal: {new_data.get('rsi_signal', 'N/A')}",
                    f"Interprétation: {new_data.get('rsi_interpretation', 'N/A')}",
                    "⚠️ Risque élevé de correction/dump imminent"
                ]
            })
        
        # 🆕 2. ALERTE RSI SURVENDU (Opportunité)
        elif new_data.get('rsi_value', 50) <= 30:
            alert_type = "info"
            alerts_list.append({
                "type": "rsi_oversold",
                "severity": "info",
                "message": f"💎 RSI SURVENDU: {new_data['rsi_value']}/100",
                "details": [
                    f"Signal: {new_data.get('rsi_signal', 'N/A')}",
                    "💡 Potentiel rebond technique possible",
                    "Vérifier les autres indicateurs avant d'investir"
                ]
            })
        
        # 🆕 3. ALERTE FIBONACCI - ZONE DE RÉSISTANCE
        if new_data.get('fibonacci_percentage', 0) >= 78.6:
            alert_type = "warning" if alert_type == "info" else alert_type
            alerts_list.append({
                "type": "fibonacci_resistance",
                "severity": "warning",
                "message": f"📐 Près de la résistance Fibonacci ({new_data['fibonacci_percentage']:.1f}%)",
                "details": [
                    f"Position: {new_data.get('fibonacci_position', 'N/A')}",
                    "⚠️ Zone dangereuse, risque de rejet",
                    "Surveiller les volumes et le RSI"
                ]
            })
        
        # 🆕 4. ALERTE FIBONACCI - ZONE DE SUPPORT
        elif new_data.get('fibonacci_percentage', 0) <= 23.6:
            alerts_list.append({
                "type": "fibonacci_support",
                "severity": "info",
                "message": f"📐 Près du support Fibonacci ({new_data['fibonacci_percentage']:.1f}%)",
                "details": [
                    f"Position: {new_data.get('fibonacci_position', 'N/A')}",
                    "💡 Zone de support possible",
                    "Potentiel rebond si le support tient"
                ]
            })
        
        # 5. PUMP & DUMP DÉTECTÉ (adapté nouveaux tokens)
        if new_data.get('is_pump_dump_suspect') and new_data.get('pump_dump_score', 0) >= 50:
            alert_type = "critical"
            token_age = new_data.get('token_age_hours', 'N/A')
            age_text = f" (Token de {token_age}h)" if token_age != 'N/A' else ""
            
            alerts_list.append({
                "type": "pump_dump",
                "severity": "critical",
                "message": f"🚨 PUMP & DUMP DÉTECTÉ{age_text} ! Score: {new_data['pump_dump_score']}/100",
                "details": new_data.get('pump_dump_warnings', [])[:5]  # Max 5 warnings
            })
        
        # 6. CHANGEMENT DE PRIX IMPORTANT
        price_change = new_data.get('market', {}).get('price_change_24h', 0)
        if abs(price_change) >= 50:
            severity = "critical" if abs(price_change) >= 100 else "warning"
            if price_change > 0:
                alerts_list.append({
                    "type": "price_spike",
                    "severity": severity,
                    "message": f"📈 Prix +{price_change:.1f}% en 24h !",
                    "details": [
                        "Vérifier le RSI pour confirmer la tendance",
                        "Attention au pump & dump"
                    ]
                })
            else:
                alerts_list.append({
                    "type": "price_drop",
                    "severity": severity,
                    "message": f"📉 Prix {price_change:.1f}% en 24h !",
                    "details": [
                        "Possible dump en cours",
                        "Vérifier la liquidité et les volumes"
                    ]
                })
            
            if severity == "critical":
                alert_type = "critical"
        
        # 7. LIQUIDITÉ CRITIQUE
        liquidity = new_data.get('market', {}).get('liquidity_usd', 0)
        if liquidity < 5000:
            alert_type = "critical"
            alerts_list.append({
                "type": "low_liquidity",
                "severity": "critical",
                "message": f"💧 Liquidité très faible: ${liquidity:,.0f}",
                "details": ["Risque de rug pull élevé", "Difficile de vendre sans slippage"]
            })
        
        # 8. HONEYPOT DÉTECTÉ
        if new_data.get('security', {}).get('is_honeypot'):
            alert_type = "critical"
            alerts_list.append({
                "type": "honeypot",
                "severity": "critical",
                "message": "🚫 HONEYPOT DÉTECTÉ !",
                "details": ["Ne pas acheter ce token", "Impossible de vendre"]
            })
        
        # 9. AUGMENTATION DU RISQUE
        new_risk = new_data.get('risk_score', 0)
        if new_risk >= 70:
            alert_type = "critical"
            alerts_list.append({
                "type": "high_risk",
                "severity": "critical",
                "message": f"⚠️ Score de risque très élevé: {new_risk}/100",
                "details": new_data.get('warnings', [])[:5]
            })
        
        # 🆕 10. CONCENTRATION ÉLEVÉE DES HOLDERS
        top_holders = new_data.get('security', {}).get('top_holders', [])
        if top_holders:
            top_5_concentration = sum(h.get('percent', 0) for h in top_holders[:5])
            if top_5_concentration > 50:
                alert_type = "critical" if alert_type != "critical" else alert_type
                alerts_list.append({
                    "type": "high_concentration",
                    "severity": "critical",
                    "message": f"👥 Concentration Top 5: {top_5_concentration:.1f}%",
                    "details": [
                        "Plus de 50% détenu par 5 wallets",
                        "Risque de manipulation élevé",
                        f"Top holder: {top_holders[0].get('percent', 0):.1f}%"
                    ]
                })
        
        # Si des alertes ont été détectées, créer l'objet d'alerte
        if alerts_list:
            return {
                "token_address": new_data['address'],
                "token_chain": new_data['chain'],
                "token_icon": new_data.get('icon', ''),
                "alert_type": alert_type,
                "alerts": alerts_list,
                "token_data": new_data,
                "timestamp": datetime.now().isoformat(),
                # 🆕 Nouvelles métriques
                "rsi_value": new_data.get('rsi_value'),
                "rsi_signal": new_data.get('rsi_signal'),
                "fibonacci_percentage": new_data.get('fibonacci_percentage'),
                "pump_dump_score": new_data.get('pump_dump_score'),
                "token_age_hours": new_data.get('token_age_hours')
            }
        
        return None
    
    def _save_alert_to_db(self, user_id: int, alert: Dict):
        """Sauvegarde une alerte dans la base de données"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_address TEXT NOT NULL,
                    token_chain TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    alert_data TEXT NOT NULL,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            import json
            cursor.execute('''
                INSERT INTO alerts (user_id, token_address, token_chain, alert_type, alert_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, alert['token_address'], alert['token_chain'], 
                  alert['alert_type'], json.dumps(alert)))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"    ❌ Erreur sauvegarde alerte: {e}")
    
    def _create_web_notification(self, user_id: int, alert: Dict):
        """Crée une notification web pour l'utilisateur"""
        pass
    
    def send_email_alert(self, to_email: str, username: str, alerts: List[Dict]):
        """Envoie un email d'alerte HTML avec RSI et Fibonacci"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 {len(alerts)} Alerte(s) Token Scanner Pro"
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            
            html_content = self._generate_email_html(username, alerts)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"  ✅ Email envoyé à {to_email}")
            
        except Exception as e:
            print(f"  ❌ Erreur envoi email: {e}")
    
    def _generate_email_html(self, username: str, alerts: List[Dict]) -> str:
        """🆕 Génère un email HTML avec RSI, Fibonacci et métriques avancées"""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #0A0E27;
            color: #E8EAF6;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #141B3A;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 900;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 16px;
        }}
        .content {{
            padding: 30px;
        }}
        .greeting {{
            font-size: 18px;
            margin-bottom: 20px;
        }}
        .alert-card {{
            background: #1A2238;
            border: 2px solid;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .alert-card.critical {{
            border-color: #F44336;
            background: linear-gradient(135deg, rgba(244, 67, 54, 0.1) 0%, rgba(233, 30, 99, 0.1) 100%);
        }}
        .alert-card.warning {{
            border-color: #FF9800;
            background: linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, rgba(255, 193, 7, 0.1) 100%);
        }}
        .alert-card.info {{
            border-color: #4A90E2;
            background: linear-gradient(135deg, rgba(74, 144, 226, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        }}
        .token-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .token-icon {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: #0A0E27;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }}
        .token-info {{
            flex: 1;
        }}
        .token-address {{
            font-family: 'Courier New', monospace;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        .token-chain {{
            font-size: 12px;
            color: #9FA8DA;
            text-transform: uppercase;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 15px;
            padding: 15px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }}
        .metric-item {{
            text-align: center;
        }}
        .metric-label {{
            font-size: 11px;
            color: #9FA8DA;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 18px;
            font-weight: 700;
        }}
        .metric-value.critical {{
            color: #F44336;
        }}
        .metric-value.warning {{
            color: #FF9800;
        }}
        .metric-value.success {{
            color: #4CAF50;
        }}
        .alert-item {{
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid;
        }}
        .alert-item.critical {{
            border-left-color: #F44336;
        }}
        .alert-item.warning {{
            border-left-color: #FF9800;
        }}
        .alert-item.info {{
            border-left-color: #4A90E2;
        }}
        .alert-message {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .alert-details {{
            font-size: 13px;
            color: #9FA8DA;
            line-height: 1.6;
        }}
        .alert-details li {{
            margin-bottom: 5px;
        }}
        .footer {{
            background: #0A0E27;
            padding: 20px 30px;
            text-align: center;
            font-size: 13px;
            color: #9FA8DA;
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Token Scanner Pro</h1>
            <p>Alerte sur vos tokens favoris</p>
        </div>
        
        <div class="content">
            <div class="greeting">
                Bonjour <strong>{username}</strong> 👋
            </div>
            <p>Nous avons détecté <strong>{len(alerts)} alerte(s) importante(s)</strong> sur vos tokens favoris :</p>
"""
        
        # Alertes
        for alert in alerts:
            token_addr = alert['token_address']
            short_addr = token_addr[:8] + '...' + token_addr[-6:]
            token_chain = alert['token_chain'].upper()
            alert_type = alert['alert_type']
            
            icon = alert.get('token_icon', '')
            icon_html = f'<img src="{icon}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;" />' if icon else '🪙'
            
            # 🆕 Métriques avancées
            rsi_value = alert.get('rsi_value')
            fibonacci_pct = alert.get('fibonacci_percentage')
            pump_score = alert.get('pump_dump_score')
            token_age = alert.get('token_age_hours')
            
            html += f"""
            <div class="alert-card {alert_type}">
                <div class="token-header">
                    <div class="token-icon">{icon_html}</div>
                    <div class="token-info">
                        <div class="token-address">{short_addr}</div>
                        <div class="token-chain">{token_chain}</div>
                    </div>
                </div>
                
                <div class="metrics-grid">
"""
            
            # Afficher les métriques disponibles
            if rsi_value is not None:
                rsi_class = "critical" if rsi_value >= 70 else "warning" if rsi_value >= 50 else "success"
                html += f"""
                    <div class="metric-item">
                        <div class="metric-label">📊 RSI</div>
                        <div class="metric-value {rsi_class}">{rsi_value}</div>
                    </div>
"""
            
            if fibonacci_pct is not None:
                fib_class = "critical" if fibonacci_pct >= 78.6 else "warning" if fibonacci_pct >= 61.8 else "success"
                html += f"""
                    <div class="metric-item">
                        <div class="metric-label">📐 Fibonacci</div>
                        <div class="metric-value {fib_class}">{fibonacci_pct:.1f}%</div>
                    </div>
"""
            
            if pump_score is not None and pump_score > 0:
                pump_class = "critical" if pump_score >= 70 else "warning" if pump_score >= 50 else "success"
                html += f"""
                    <div class="metric-item">
                        <div class="metric-label">🚨 Pump Score</div>
                        <div class="metric-value {pump_class}">{pump_score}/100</div>
                    </div>
"""
            
            if token_age != 'N/A' and token_age is not None:
                html += f"""
                    <div class="metric-item">
                        <div class="metric-label">🆕 Âge Token</div>
                        <div class="metric-value">{token_age}h</div>
                    </div>
"""
            
            html += """
                </div>
"""
            
            for item in alert['alerts']:
                severity = item['severity']
                html += f"""
                <div class="alert-item {severity}">
                    <div class="alert-message">{item['message']}</div>
"""
                
                if item.get('details'):
                    html += '<ul class="alert-details">'
                    for detail in item['details'][:3]:
                        html += f'<li>{detail}</li>'
                    html += '</ul>'
                
                html += '</div>'
            
            html += '</div>'
        
        # Footer
        html += f"""
        </div>
        
        <div class="footer">
            <p>Cette alerte a été générée automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            <a href="http://localhost:5000" class="btn">📊 Voir le dashboard</a>
            <p style="margin-top: 20px; font-size: 11px;">
                Token Scanner Pro - Surveillance automatique avec RSI & Fibonacci<br/>
                Vous recevez cet email car vous êtes un utilisateur Premium
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def get_user_alerts(self, user_id: int, limit: int = 20, unread_only: bool = False):
        """Récupère les alertes d'un utilisateur"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT id, token_address, token_chain, alert_type, alert_data, is_read, created_at
                FROM alerts
                WHERE user_id = ?
            '''
            
            if unread_only:
                query += ' AND is_read = 0'
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            
            cursor.execute(query, (user_id, limit))
            
            import json
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'id': row[0],
                    'token_address': row[1],
                    'token_chain': row[2],
                    'alert_type': row[3],
                    'alert_data': json.loads(row[4]),
                    'is_read': row[5],
                    'created_at': row[6]
                })
            
            conn.close()
            return alerts
            
        except Exception as e:
            print(f"Erreur récupération alertes: {e}")
            return []
    
    def mark_alert_as_read(self, alert_id: int):
        """Marque une alerte comme lue"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE alerts SET is_read = 1 WHERE id = ?', (alert_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erreur marquage alerte: {e}")
            return False
    
    def get_unread_count(self, user_id: int) -> int:
        """Compte le nombre d'alertes non lues"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM alerts WHERE user_id = ? AND is_read = 0',
                (user_id,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"Erreur comptage alertes: {e}")
            return 0


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    # Configuration SMTP (exemple avec Gmail)
    alert_system = AlertSystem(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_user="votre.email@gmail.com",  # Remplacer
        smtp_password="votre_app_password"   # Remplacer
    )
    
    # Démarrer la surveillance automatique
    alert_system.start_monitoring()
    
    # Le script tourne en continu
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt de la surveillance...")
        alert_system.stop_monitoring()