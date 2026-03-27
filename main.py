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
def home(): return "PredictPro Vision Large est en ligne !"

def run():
    app.run(host='0.0.0.0', port=10000)

# --- 2. CONFIGURATION DU BOT (AVEC TON NOUVEAU TOKEN) ---
TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 

bot = telebot.TeleBot(TOKEN)

# --- 3. LOGIQUE MATHÉMATIQUE ---
def calculer_stats(m_dom, m_ext):
    p_win = 0
    # On calcule la probabilité de victoire domicile (Loi de Poisson)
    for i in range(1, 7):
        for j in range(0, i):
            p_win += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_win * 100, 1)

# --- 4. ENVOI DE L'ANALYSE GRAPHIQUE ---
def envoyer_analyse(h, a, p_bot, p_book, cote, sport):
    try:
        value = p_bot - p_book
        # Système de feux tricolores selon la rentabilité
        if value > 5: icon, color = "✅", "#27ae60" # Excellent
        elif value > 0: icon, color = "🟡", "#f1c40f" # Neutre/Correct
        else: icon, color = "🔴", "#e74c3c" # Risqué

        plt.figure(figsize=(6,3.5))
        plt.bar(['PredictPro', 'Bookmaker'], [p_bot, p_book], color=[color, '#bdc3c7'])
        plt.title(f"{h} vs {a} ({sport})")
        plt.ylim(0, 100)
        
        # Nom de fichier unique pour éviter les conflits d'écriture
        path = f"img_{int(time.time())}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"{icon} **ANALYSE : {h}**\n"
               f"🏆 Sport : {sport}\n"
               f"📈 Cote : {cote}\n"
               f"📊 Proba Bot : {p_bot}%\n"
               f"💰 Value : {round(value, 1)}%")
        
        with open(path, "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
    except Exception as e:
        print(f"Erreur envoi image : {e}")

# --- 5. LE RADAR PANORAMIQUE ---
def lancer_scan_large():
    championnats = [
        "soccer_france_ligue_1", "soccer_spain_la_liga", "soccer_germany_bundesliga", 
        "soccer_italy_serie_a", "soccer_england_premier_league", "soccer_netherlands_ere_divisie",
        "baseball_mlb", "basketball_nba", "icehockey_nhl", "soccer_usa_mls",
        "soccer_portugal_primeira_liga", "soccer_turkey_super_league"
    ]
    
    bot.send_message(CHAT_ID, "🌐 **Lancement du Scan Panoramique...**\nAnalyse des championnats mondiaux en cours.")
    
    matchs_total = 0
    for ligue in championnats:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{ligue}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            events = requests.get(url).json()
            
            if isinstance(events, list) and len(events) > 0:
                # On analyse les 3 premiers matchs de chaque ligue
                for m in events[:3]:
                    matchs_total += 1
                    h, a = m['home_team'], m['away_team']
                    
                    for bookie in m['bookmakers'][:1]:
                        outcomes = bookie['markets'][0]['outcomes']
                        try:
                            cote = next(o['price'] for o in outcomes if o['name'] == h)
                            p_bot = calculer_stats(2.1, 1.2) # Puissance simulée
                            p_book = (1/cote)*100
                            envoyer_analyse(h, a, p_bot, p_book, cote, ligue)
                        except: continue
            time.sleep(0.5) # Pause légère pour respecter l'API
        except: continue
        
    bot.send_message(CHAT_ID, f"🏁 **Scan Terminé**\n{matchs_total} matchs analysés.")

# --- 6. COMMANDES ---
@bot.message_handler(commands=['scan'])
def handle_scan(message):
    lancer_scan_large()

@bot.message_handler(commands=['start', 'aide'])
def handle_start(message):
    bot.reply_to(message, "🤖 **PredictPro Panoramique**\n\nCommandes :\n/scan : Analyse complète\n/aide : Affiche ce message")

# --- 7. DÉMARRAGE ET SURVIE ---
if __name__ == "__main__":
    # Lancement du serveur web
    Thread(target=run, daemon=True).start()
    
    print("🤖 Tentative de démarrage du bot...")
    
    while True:
        try:
            # Nettoyage des webhooks précédents
            bot.remove_webhook()
            time.sleep(1)
            
            # Message de confirmation sur Telegram
            bot.send_message(CHAT_ID, "🚀 **Bot PredictPro Connecté !**\nLe nouveau Token est valide. Tapez /scan pour tester.")
            
            print("✅ Bot opérationnel !")
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"🔄 Erreur de connexion : {e}. Nouvelle tentative dans 10s...")
            time.sleep(10)
