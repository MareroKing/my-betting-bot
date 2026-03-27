import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION SERVEUR ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro Multi-Sports is Live!"
def run(): app.run(host='0.0.0.0', port=10000)

# --- 2. VOS PARAMÈTRES ---
TOKEN = "8695595150:AAHyiKL9bX0rMqiVBZ27hAoE0WsyiK9XUnQ"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 
bot = telebot.TeleBot(TOKEN)

# --- 3. LOGIQUE MATHÉMATIQUE ---
def probas_completes(m_dom, m_ext):
    p_victoire_dom = 0
    p_over_15 = 0
    for i in range(0, 8): # On monte à 8 pour le Baseball/Hockey
        for j in range(0, 8): 
            prob = poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
            if i > j: p_victoire_dom += prob
            if (i + j) > 1.5: p_over_15 += prob
    return {
        "win": round(p_victoire_dom * 100, 1),
        "over15": round(p_over_15 * 100, 1)
    }

# --- 4. ENVOI DES ALERTES ---
def envoyer_alerte_graphique(h, a, type_pari, p_bot, p_book, cote, sport):
    try:
        plt.figure(figsize=(7,4))
        plt.bar(['PredictPro', 'Bookmaker'], [p_bot, p_book], color=['#27ae60', '#e67e22'])
        plt.axhline(y=p_book, color='red', linestyle='--', alpha=0.5)
        plt.title(f"{type_pari} : {h} vs {a}")
        plt.ylim(0, 100)
        
        path = "analyse_temp.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"🎯 **OPPORTUNITÉ DÉTECTÉE**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"🏆 **Sport/Ligue :** {sport}\n"
               f"📈 **Cote :** {cote}\n"
               f"🔥 **Confiance Bot :** {p_bot}%\n"
               f"📊 **Confiance Marché :** {p_book:.1f}%")
        
        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
    except Exception as e: print(f"❌ Erreur graphique : {e}")

# --- 5. MOTEUR DE SCAN ÉLARGI ---
def lancer_scan():
    print("🚀 Scan des ligues mondiales...")
    # Liste optimisée pour trouver des matchs MAINTENANT
    sports = [
        "soccer_france_ligue_1", "soccer_spain_la_liga", 
        "soccer_italy_serie_a", "soccer_germany_bundesliga",
        "soccer_portugal_primeira_liga", "soccer_belgium_first_division_a",
        "baseball_mlb", "icehockey_nhl", "basketball_nba"
    ]
    
    matchs_vus = 0
    alertes_envoyees = 0
    
    for s in sports:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{s}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h,totals"
            response = requests.get(url)
            
            # Protection si l'API est saturée ou vide
            if response.status_code != 200: continue
            events = response.json()
            
            if isinstance(events, list) and len(events) > 0:
                for m in events[:10]:
                    matchs_vus += 1
                    h, a = m['home_team'], m['away_team']
                    stats = probas_completes(2.1, 1.2) # Moyenne test
                    
                    for bookie in m['bookmakers'][:1]:
                        for market in bookie['markets']:
                            # Analyse Victoire
                            if market['key'] == 'h2h':
                                try:
                                    cote = next(o['price'] for o in market['outcomes'] if o['name'] == h)
                                    p_book = (1/cote)*100
                                    if stats['win'] > (p_book + 1): # +1% pour le test
                                        envoyer_alerte_graphique(h, a, "VICTOIRE", stats['win'], p_book, cote, s)
                                        alertes_envoyees += 1
                                except: continue
        except Exception as e: 
            print(f"⚠️ Erreur sur {s}")
            continue

    # Rapport Final
    rapport = (f"📊 **COMPTE-RENDU DU RADAR**\n\n"
               f"✅ Matchs analysés : {matchs_vus}\n"
               f"🔥 Alertes générées : {alertes_envoyees}\n"
               f"⚾️ MLB Inclus dans le scan.")
    bot.send_message(CHAT_ID, rapport, parse_mode='Markdown')

# --- 6. INTERACTION & THREADS ---
@bot.message_handler(commands=['scan'])
def manual_scan(message):
    bot.reply_to(message, "🔎 Scan en cours sur Football, MLB, NHL et NBA...")
    lancer_scan()

@bot.message_handler(commands=['start', 'aide'])
def welcome(message):
    bot.reply_to(message, "🤖 **PredictPro Multi-Sports**\n/scan pour lancer l'analyse.")

def boucle_automatique():
    time.sleep(10)
    while True:
        lancer_scan()
        time.sleep(3600)

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    Thread(target=boucle_automatique, daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(5)
