import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION SERVEUR (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro Radar is Live!"
def run(): app.run(host='0.0.0.0', port=10000)

# --- 2. VOS PARAMÈTRES ---
TOKEN = "8695595150:AAHyiKL9bX0rMqiVBZ27hAoE0WsyiK9XUnQ"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 
bot = telebot.TeleBot(TOKEN)

# --- 3. LOGIQUE MATHÉMATIQUE (Poisson) ---
def probas_completes(m_dom, m_ext):
    p_victoire_dom = 0
    p_over_15 = 0
    for i in range(0, 6): 
        for j in range(0, 6): 
            prob = poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
            if i > j: p_victoire_dom += prob
            if (i + j) > 1.5: p_over_15 += prob
    return {
        "win": round(p_victoire_dom * 100, 1),
        "over15": round(p_over_15 * 100, 1)
    }

# --- 4. GÉNÉRATION ET ENVOI DE L'ANALYSE ---
def envoyer_alerte_graphique(h, a, type_pari, p_bot, p_book, cote, sport):
    try:
        plt.figure(figsize=(7,4))
        plt.bar(['PredictPro', 'Bookmaker'], [p_bot, p_book], color=['#27ae60', '#e67e22'])
        plt.axhline(y=p_book, color='red', linestyle='--', alpha=0.5)
        plt.title(f"{type_pari} : {h} vs {a}")
        plt.ylabel("Probabilité (%)")
        plt.ylim(0, 100)
        
        path = "analyse_temp.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"🎯 **OPPORTUNITÉ DÉTECTÉE**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"🏆 **Type :** {type_pari}\n"
               f"📈 **Cote :** {cote}\n"
               f"🔥 **Confiance Bot :** {p_bot}%\n"
               f"📊 **Confiance Marché :** {p_book:.1f}%")
        
        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
    except Exception as e: print(f"❌ Erreur graphique : {e}")

# --- 5. MOTEUR DE SCAN AVEC RAPPORT ---
def lancer_scan():
    print("🚀 Scan des marchés en cours...")
    sports = ["soccer_france_ligue_1", "soccer_spain_la_liga", "soccer_germany_bundesliga", "icehockey_nhl", "baseball_mlb"]
    matchs_vus = 0
    alertes_envoyees = 0
    
    for s in sports:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{s}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h,totals"
            events = requests.get(url).json()
            
            if isinstance(events, list):
                for m in events[:10]: # On regarde les 10 prochains matchs
                    matchs_vus += 1
                    h, a = m['home_team'], m['away_team']
                    stats = probas_completes(2.1, 1.2) # Puissance fixée (à dynamiser demain)
                    
                    for bookie in m['bookmakers'][:1]:
                        for market in bookie['markets']:
                            # Analyse Victoire (H2H)
                            if market['key'] == 'h2h':
                                cote = next(o['price'] for o in market['outcomes'] if o['name'] == h)
                                p_book = (1/cote)*100
                                # SEUIL BAS POUR TEST : +1% de value
                                if stats['win'] > (p_book + 1): 
                                    envoyer_alerte_graphique(h, a, "VICTOIRE", stats['win'], p_book, cote, s)
                                    alertes_envoyees += 1
                            
                            # Analyse Over 1.5
                            elif market['key'] == 'totals':
                                for out in market['outcomes']:
                                    if out['name'] == 'Over' and out['point'] == 1.5:
                                        p_book = (1/out['price'])*100
                                        # SEUIL BAS POUR TEST : Proba > 50%
                                        if stats['over15'] > 50:
                                            envoyer_alerte_graphique(h, a, "OVER 1.5 BUTS", stats['over15'],
