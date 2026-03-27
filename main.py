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
    return "PredictPro Bot is Live and Stable!"

def run():
    # Render utilise le port 10000 par défaut pour les Web Services
    app.run(host='0.0.0.0', port=10000)

# --- 2. VOS PARAMÈTRES ---
TOKEN = "8695595150:AAGPxvoX4bOFaKgnu9bdyzE6Nqy2Mi4pGt4"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 

bot = telebot.TeleBot(TOKEN)

# --- 3. LOGIQUE MATHÉMATIQUE (Loi de Poisson) ---
def calculer_proba_poisson(m_dom, m_ext):
    p_gagne = 0
    for i in range(1, 6): 
        for j in range(0, i): 
            p_gagne += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_gagne * 100, 1)

# --- 4. ENVOI DES ALERTES GRAPHIQUES ---
def generer_et_envoyer(h, a, p_bot, p_book, cote, sport):
    try:
        plt.figure(figsize=(7,4))
        plt.bar(['PredictPro', 'Bookmaker'], [p_bot, p_book], color=['#27ae60', '#7f8c8d'])
        plt.axhline(y=p_book, color='red', linestyle='--', alpha=0.5)
        plt.title(f"Analyse Value : {h}")
        plt.ylabel("Probabilité (%)")
        plt.ylim(0, 100)
        
        plt.savefig("analyse.png")
        plt.close()
        
        msg = (f"🎯 **ALERTE VALUE DÉTECTÉE**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"🏆 **Ligue :** {sport}\n"
               f"📈 **Cote :** {cote}\n"
               f"🔥 **Confiance Bot :** {p_bot}%\n"
               f"📊 **Confiance Marché :** {p_book:.1f}%")
        
        with open("analyse.png", "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
    except Exception as e:
        print(f"Erreur envoi graphique : {e}")

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
                    
                    # Probabilité Bot (Simulée) vs Bookmaker
                    p_bot = calculer_proba_poisson(2.1, 1.2)
                    p_book = (1 / home_odds) * 100
                    
                    # Filtre d'intelligence : On n'envoie que si c'est une vraie "Value"
                    if p_bot > (p_book + 5): 
                        generer_et_envoyer(home, m['away_team'], p_bot, p_book, home_odds, s)
        except: continue
    print("✅ Fin du scan.")

# --- 6. COMMANDES INTERACTIVES ---
@bot.message_handler(commands=['start', 'aide'])
def send_welcome(message):
    help_text = (
        "🤖 **Assistant PredictPro**\n\n"
        "Je surveille les cotes pour toi.\n"
        "👉 `/scan` : Lance une analyse manuelle immédiate.\n"
        "👉 `/aide` : Affiche ce menu."
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['scan'])
def manual_scan(message):
    bot.reply_to(message, "🔎 Scan manuel demandé... Analyse en cours.")
    lancer_scan()
    bot.send_message(CHAT_ID, "✅ Scan manuel terminé.")

# --- 7. MULTI-THREADING ET ÉVITEMENT DE CONFLIT ---
def boucle_automatique():
    # Attente initiale pour laisser le polling démarrer proprement
    time.sleep(10)
    while True:
        lancer_scan()
        time.sleep(3600)

if __name__ == "__main__":
    # Thread 1 : Serveur Web pour Render
    t_server = Thread(target=run)
    t_server.daemon = True
    t_server.start()

    # Thread 2 : Boucle de Scan Auto
    t_scan = Thread(target=boucle_automatique)
    t_scan.daemon = True
    t_scan.start()

    print("🤖 Bot PredictPro prêt !")

    # --- SÉCURITÉ ANTI-CONFLIT (ERREUR 409) ---
    try:
        # On force la suppression de toute ancienne connexion
        bot.remove_webhook()
        time.sleep(1)
        # On lance l'écoute des messages
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Erreur fatale Polling : {e}")
