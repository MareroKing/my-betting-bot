import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro Vision Large is Live!"
def run(): app.run(host='0.0.0.0', port=10000)

TOKEN = "8695595150:AAHyiKL9bX0rMqiVBZ27hAoE0WsyiK9XUnQ"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 
bot = telebot.TeleBot(TOKEN)

# --- 2. CALCULS ---
def calculer_stats(m_dom, m_ext):
    p_win = 0
    for i in range(1, 7):
        for j in range(0, i):
            p_win += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_win * 100, 1)

# --- 3. ENVOI DE L'ANALYSE ---
def envoyer_analyse(h, a, p_bot, p_book, cote, sport):
    try:
        value = p_bot - p_book
        # Signal visuel de l'opportunité
        if value > 5: icon, color = "✅", "#27ae60"
        elif value > 0: icon, color = "🟡", "#f1c40f"
        else: icon, color = "🔴", "#e74c3c"

        plt.figure(figsize=(6,3.5))
        plt.bar(['Bot', 'Bookie'], [p_bot, p_book], color=[color, '#bdc3c7'])
        plt.title(f"{h} vs {a} ({sport})")
        plt.ylim(0, 100)
        
        path = f"img_{h[:3]}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"{icon} **ANALYSE : {h}**\n"
               f"🏆 Sport : {sport}\n"
               f"📈 Cote : {cote}\n"
               f"📊 Proba Bot : {p_bot}%\n"
               f"💰 Value : {round(value, 1)}%")
        
        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
    except: pass

# --- 4. LE RADAR PANORAMIQUE ---
def lancer_scan_large():
    # Liste exhaustive des championnats majeurs mondiaux
    championnats = [
        # FOOTBALL EUROPE
        "soccer_france_ligue_1", "soccer_spain_la_liga", "soccer_germany_bundesliga", 
        "soccer_italy_serie_a", "soccer_england_premier_league", "soccer_netherlands_ere_divisie",
        # USA / AMÉRIQUE
        "baseball_mlb", "basketball_nba", "icehockey_nhl", "soccer_usa_mls",
        # AUTRES (Pour avoir du flux constant)
        "soccer_portugal_primeira_liga", "soccer_turkey_super_league"
    ]
    
    bot.send_message(CHAT_ID, "🌐 **Lancement du Scan Panoramique...**\n(Analyse des 12 championnats majeurs)")
    
    matchs_total = 0
    for ligue in championnats:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{ligue}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            events = requests.get(url).json()
            
            if isinstance(events, list) and len(events) > 0:
                # On prend les 3 matchs les plus proches de CHAQUE championnat
                for m in events[:3]:
                    matchs_total += 1
                    h, a = m['home_team'], m['away_team']
                    
                    for bookie in m['bookmakers'][:1]:
                        outcomes = bookie['markets'][0]['outcomes']
                        try:
                            cote = next(o['price'] for o in outcomes if o['name'] == h)
                            p_bot = calculer_stats(2.1, 1.2) # Moyenne simulée
                            p_book = (1/cote)*100
                            envoyer_analyse(h, a, p_bot, p_book, cote, ligue)
                        except: continue
            time.sleep(1) # Pause pour éviter le ban API
        except: continue
        
    bot.send_message(CHAT_ID, f"🏁 **Scan Panoramique Terminé**\nAnalyse de {matchs_total} matchs effectuée.")

# --- 5. COMMANDES ---
@bot.message_handler(commands=['scan'])
def handle_scan(message):
    lancer_scan_large()

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
