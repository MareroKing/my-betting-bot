import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
import os # AJOUTÉ : Pour lire le port de Render
from flask import Flask
from threading import Thread

# --- 1. SERVEUR DE MAINTIEN (CORRIGÉ POUR RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "PredictPro Elite est en ligne !"

def run():
    # Render définit automatiquement un port, sinon on utilise 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [ GARDER LES SECTIONS 2 À 6 IDENTIQUES ] ---
# (Token, API Key, calculer_stats, envoyer_analyse, lancer_scan_elite, handle_scan)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

def calculer_stats(m_dom, m_ext):
    p_win = 0
    for i in range(1, 8):
        for j in range(0, i):
            p_win += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_win * 100, 1)

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
        msg = (f"{icon} **ANALYSE ÉLITE**\n\n🏟 **Match :** {h} vs {a}\n🏆 **Ligue :** {sport}\n📈 **Cote :** {cote}\n📊 **Confiance :** {p_bot}%\n💰 **Value :** {round(value, 1)}%")
        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
        time.sleep(1)
    except: pass

def lancer_scan_elite():
    flux_majeurs = ["soccer", "baseball", "basketball", "icehockey"]
    bot.send_message(CHAT_ID, "🔎 **Scan des événements majeurs en cours...**")
    matchs_total = 0
    for sport in flux_majeurs:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            events = requests.get(url).json()
            if isinstance(events, list) and len(events) > 0:
                for m in events[:10]:
                    matchs_total += 1
                    h, a, ligue = m['home_team'], m['away_team'], m.get('sport_title', sport)
                    for bookie in m['bookmakers'][:1]:
                        outcomes = bookie['markets'][0]['outcomes']
                        try:
                            cote = next(o['price'] for o in outcomes if o['name'] == h)
                            p_bot = calculer_stats(2.1, 1.2)
                            p_book = (1/cote)*100
                            envoyer_analyse(h, a, p_bot, p_book, cote, ligue)
                        except: continue
        except: continue
    bot.send_message(CHAT_ID, f"🏁 **Scan Terminé !**\n{matchs_total} analyses envoyées.")

@bot.message_handler(commands=['scan'])
def handle_scan(message): lancer_scan_elite()

# --- 7. DÉMARRAGE (CORRIGÉ POUR ÉVITER LE TIMEOUT) ---
if __name__ == "__main__":
    # 1. On lance le serveur Flask d'abord
    server_thread = Thread(target=run)
    server_thread.start()
    
    print("🚀 Serveur Web démarré pour Render")

    # 2. On attend 2 secondes que le port soit bien ouvert
    time.sleep(2)

    while True:
        try:
            bot.remove_webhook()
            bot.send_message(CHAT_ID, "⚡️ **PredictPro Elite est Live !**\nTapez /scan pour tester.")
            print("🤖 Bot Telegram à l'écoute...")
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"Relance : {e}")
            time.sleep(10)
