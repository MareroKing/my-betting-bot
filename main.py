import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION DU SERVEUR (POUR RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "PredictPro Bot is Interactive & Live!"

def run():
    app.run(host='0.0.0.0', port=10000)

# --- 2. VOS PARAMÈTRES ---
TOKEN = "8695595150:AAHyiKL9bX0rMqiVBZ27hAoE0WsyiK9XUnQ"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 

bot = telebot.TeleBot(TOKEN)

# --- 3. LOGIQUE MATHÉMATIQUE ---
def calculer_proba_poisson(m_dom, m_ext):
    p_gagne = 0
    for i in range(1, 6): 
        for j in range(0, i): 
            p_gagne += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_gagne * 100, 1)

# --- 4. ENVOI DES ALERTES ---
def generer_et_envoyer(h, a, p_bot, p_book, cote, sport):
    try:
        plt.figure(figsize=(7,4))
        plt.bar(['Bot PredictPro', 'Bookmaker'], [p_bot, p_book], color=['#27ae60', '#7f8c8d'])
        plt.axhline(y=p_book, color='red', linestyle='--', alpha=0.5)
        plt.title(f"Analyse Value : {h}")
        plt.ylim(0, 100)
        
        plt.savefig("analyse.png")
        plt.close()
        
        msg = (f"🎯 **ALERTE VALUE DÉTECTÉE**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"🏆 **Ligue :** {sport}\n"
               f"📈 **Cote :** {cote}\n"
               f"🔥 **Confiance Bot :** {p_bot}%\n"
               f"📊 **Confiance Bookie :** {p_book:.1f}%")
        
        with open("analyse.png", "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
    except Exception as e:
        print(f"Erreur envoi : {e}")

# --- 5. MOTEUR DE SCAN ---
def lancer_scan():
    print("🚀 Scan des marchés en cours...")
    sports = ["soccer_france_ligue_1", "soccer_spain_la_liga", "soccer_germany_bundesliga", "icehockey_nhl", "baseball_mlb"]
    for s in sports:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{s}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            events = requests.get(url).json()
            if isinstance(events, list):
                for m in events[:5]:
                    home = m['home_team']
                    outcomes = m['bookmakers'][0]['markets'][0]['outcomes']
                    home_odds = next(o['price'] for o in outcomes if o['name'] == home)
                    p_bot = calculer_proba_poisson(2.1, 1.2)
                    p_book = (1 / home_odds) * 100
                    if p_bot > (p_book + 5): 
                        generer_et_envoyer(home, m['away_team'], p_bot, p_book, home_odds, s)
        except: continue
    print("✅ Scan terminé.")

# --- 6. COMMANDES INTERACTIVES ---
@bot.message_handler(commands=['start', 'aide'])
def send_welcome(message):
    help_text = (
        "🤖 **Bienvenue sur PredictPro !**\n\n"
        "Je scanne le marché toutes les heures, mais tu peux me parler :\n"
        "👉 `/scan` : Pour lancer une analyse immédiate.\n"
        "👉 `/aide` : Pour voir ce message."
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['scan'])
def manual_scan(message):
    bot.reply_to(message, "🔎 Analyse manuelle lancée... Un instant.")
    lancer_scan()
    bot.send_message(CHAT_ID, "✅ Fin du scan manuel.")

# --- 7. GESTION DU MULTI-TÂCHES (THREADS) ---
def boucle_automatique():
    while True:
        lancer_scan()
        time.sleep(3600)

if __name__ == "__main__":
    t_server = Thread(target=run)
    t_server.daemon = True
    t_server.start()

    t_scan = Thread(target=boucle_automatique)
    t_scan.daemon = True
    t_scan.start()

    print("🤖 Bot PredictPro opérationnel !")
    
    # On ajoute skip_pending=True pour éviter les conflits au démarrage
    bot.infinity_polling(skip_pending=True)
