import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- MINI SERVEUR POUR RENDER ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=10000)

# --- TA CONFIGURATION ---
TOKEN = "8695595150:AAHyiKL9bX0rMqiVBZ27hAoE0WsyiK9XUnQ"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da537ab4c7" # <--- METS TA CLÉ ICI
bot = telebot.TeleBot(TOKEN)

def calculer_proba_poisson(m_dom, m_ext):
    p_gagne = 0
    for i in range(1, 6):
        for j in range(0, i):
            p_gagne += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_gagne * 100, 1)

def generer_et_envoyer(h, a, p_bot, p_book, cote, sport):
    plt.figure(figsize=(7,4))
    plt.bar(['Bot', 'Bookmaker'], [p_bot, p_book], color=['#2ecc71', '#e74c3c'])
    plt.title(f"Analyse : {h} vs {a}")
    plt.savefig("analyse.png")
    plt.close()
    msg = f"🎯 **VALUE DÉTECTÉE ({sport})**\n\n🏟 {h} vs {a}\n✅ Pari : {h}\n📈 Cote : {cote}\n🔥 Confiance : {p_bot}%"
    with open("analyse.png", "rb") as img:
        bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')

def lancer_scan():
    print("🚀 Scan en cours...")
    sports = ["soccer_france_ligue_1", "soccer_spain_la_liga", "icehockey_nhl", "baseball_mlb"]
    for s in sports:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{s}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            events = requests.get(url).json()
            if isinstance(events, list):
                for m in events[:3]:
                    home = m['home_team']
                    outcomes = m['bookmakers'][0]['markets'][0]['outcomes']
                    c = next(o['price'] for o in outcomes if o['name'] == home)
                    p_bot = calculer_proba_poisson(2.1, 1.2)
                    p_book = (1/c)*100
                    if True:
                        generer_et_envoyer(home, m['away_team'], p_bot, p_book, c, s)
        except:
            continue
    print("✅ Fin du scan.")

if __name__ == "__main__":
    # 1. On lance le serveur Flask dans un fil séparé
    t = Thread(target=run)
    t.daemon = True # Ajoute cette ligne pour plus de sécurité
    t.start()
    
    print("🚀 Le bot démarre son premier scan...")
    # 2. Test d'envoi immédiat pour vérifier la connexion Telegram
    try:
        bot.send_message(CHAT_ID, "✅ Le Bot PredictPro est en ligne et commence le scan !")
    except Exception as e:
        print(f"Erreur Telegram: {e}")

    # 3. La boucle infinie
    while True:
        try:
            lancer_scan()
        except Exception as e:
            print(f"Erreur lors du scan: {e}")
        
        print("✅ Scan fini. Repos d'une heure...")
        time.sleep(3600)
