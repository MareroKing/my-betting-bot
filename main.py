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
    return "PredictPro Bot is Live!"

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
        plt.bar(['Bot PredictPro', 'Bookmaker'], [p_bot, p_book], color=['#27ae60', '#c0392b'])
        plt.title(f"Analyse de Marché : {h}")
        plt.ylabel("Probabilité de Victoire (%)")
        plt.ylim(0, 100)
        
        plt.savefig("analyse.png")
        plt.close()
        
        msg = (f"🎯 **TEST D'ALERTE RÉUSSI**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"🏆 **Ligue :** {sport}\n"
               f"📈 **Cote :** {cote}\n"
               f"🔥 **Confiance Bot :** {p_bot}%")
        
        with open("analyse.png", "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
        print(f"✅ Message envoyé pour {h}")
    except Exception as e:
        print(f"❌ Erreur envoi : {e}")

# --- 5. MOTEUR DE SCAN ---
def lancer_scan():
    print("🚀 Scan des opportunités en cours...")
    sports = ["soccer_france_ligue_1", "soccer_spain_la_liga", "icehockey_nhl", "baseball_mlb"]
    
    for s in sports:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{s}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            events = requests.get(url).json()
            
            if isinstance(events, list) and len(events) > 0:
                # On teste les 2 premiers matchs de chaque sport
                for m in events[:2]:
                    home = m['home_team']
                    away = m['away_team']
                    outcomes = m['bookmakers'][0]['markets'][0]['outcomes']
                    home_odds = next(o['price'] for o in outcomes if o['name'] == home)
                    
                    p_bot = calculer_proba_poisson(2.1, 1.2)
                    p_book = (1 / home_odds) * 100
                    
                    # --- TEST FORCÉ (IF TRUE) ---
                    if p_bot > (p_book + 5) 
                        generer_et_envoyer(home, away, p_bot, p_book, home_odds, s)
            else:
                print(f"ℹ️ Pas de données pour {s}")
        except Exception as e:
            print(f"⚠️ Erreur scan {s} : {e}")
            continue
    print("✅ Scan terminé.")

# --- 6. DÉMARRAGE DU BOT ---
if __name__ == "__main__":
    # Lancement du serveur web pour Render
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
    print("🤖 Bot PredictPro Initialisé.")
    
    # Petit délai pour laisser le serveur démarrer
    time.sleep(2)
    
    try:
        bot.send_message(CHAT_ID, "🚀 **DÉPLOIEMENT RÉUSSI !**\nLe bot est en ligne et lance son premier scan forcé...")
    except Exception as e:
        print(f"Erreur Telegram : {e}")

    # Boucle de scan infinie
    while True:
        lancer_scan()
        print("💤 Repos d'une heure...")
        time.sleep(3600)
