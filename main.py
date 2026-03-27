import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- 1. SERVEUR DE MAINTIEN ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro Elite est en ligne !"
def run(): app.run(host='0.0.0.0', port=10000)

# --- 2. CONFIGURATION (TOKEN & NOUVELLE CLÉ) ---
TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a" 

bot = telebot.TeleBot(TOKEN)

# --- 3. MATHÉMATIQUES (LOI DE POISSON) ---
def calculer_stats(m_dom, m_ext):
    p_win = 0
    for i in range(1, 8):
        for j in range(0, i):
            p_win += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_win * 100, 1)

# --- 4. ENVOI DE L'ANALYSE ---
def envoyer_analyse(h, a, p_bot, p_book, cote, sport):
    try:
        value = p_bot - p_book
        icon = "✅" if value > 2 else "🔴"
        color = "#27ae60" if value > 2 else "#e74c3c"

        plt.figure(figsize=(6,3.5))
        plt.bar(['Bot', 'Bookie'], [p_bot, p_book], color=[color, '#bdc3c7'])
        plt.title(f"{h} vs {a}")
        plt.ylim(0, 100)
        
        path = f"img_{int(time.time())}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"{icon} **ANALYSE ÉLITE**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"🏆 **Ligue :** {sport}\n"
               f"📈 **Cote :** {cote}\n"
               f"📊 **Confiance :** {p_bot}%\n"
               f"💰 **Value :** {round(value, 1)}%")
        
        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
        time.sleep(1) # Pause anti-spam Telegram
    except: pass

# --- 5. LE SCAN DES ÉVÉNEMENTS MAJEURS ---
def lancer_scan_elite():
    # On cible les flux globaux pour ne jamais être à vide
    flux_majeurs = ["soccer", "baseball", "basketball", "icehockey"]
    
    bot.send_message(CHAT_ID, "🔎 **Scan des événements majeurs en cours...**")
    
    matchs_total = 0
    for sport in flux_majeurs:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            events = requests.get(url).json()
            
            if isinstance(events, list) and len(events) > 0:
                # On prend les 10 meilleurs matchs de chaque catégorie
                for m in events[:10]:
                    matchs_total += 1
                    h = m['home_team']
                    a = m['away_team']
                    ligue = m.get('sport_title', sport)
                    
                    for bookie in m['bookmakers'][:1]:
                        outcomes = bookie['markets'][0]['outcomes']
                        try:
                            cote = next(o['price'] for o in outcomes if o['name'] == h)
                            p_bot = calculer_stats(2.1, 1.2) # Moyenne de base
                            p_book = (1/cote)*100
                            envoyer_analyse(h, a, p_bot, p_book, cote, ligue)
                        except: continue
        except: continue
        
    if matchs_total == 0:
        bot.send_message(CHAT_ID, "⚠️ Aucun match trouvé. Vérifiez l'activation de la clé API.")
    else:
        bot.send_message(CHAT_ID, f"🏁 **Scan Terminé !**\n{matchs_total} analyses envoyées.")

# --- 6. COMMANDES ---
@bot.message_handler(commands=['scan'])
def handle_scan(message):
    lancer_scan_elite()

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "🚀 **PredictPro Elite Prêt !**\nTape /scan pour voir les gros matchs du jour.")

# --- 7. DÉMARRAGE ---
if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.send_message(CHAT_ID, "⚡️ **Système Opérationnel !**\nNouvelle clé API connectée. Tapez /scan.")
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(10)
