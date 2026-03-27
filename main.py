import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- 1. SERVEUR DE MAINTIEN (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro Full Vision is Live!"
def run(): app.run(host='0.0.0.0', port=10000)

# --- 2. CONFIGURATION ---
TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 

bot = telebot.TeleBot(TOKEN)

# --- 3. LOGIQUE MATHÉMATIQUE ---
def calculer_stats(m_dom, m_ext):
    p_win = 0
    # Loi de Poisson pour estimer la probabilité de victoire à domicile
    for i in range(1, 8):
        for j in range(0, i):
            p_win += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_win * 100, 1)

# --- 4. ENVOI DE L'ANALYSE ---
def envoyer_analyse(h, a, p_bot, p_book, cote, sport):
    try:
        value = p_bot - p_book
        if value > 5: icon, color = "✅", "#27ae60"
        elif value > 0: icon, color = "🟡", "#f1c40f"
        else: icon, color = "🔴", "#e74c3c"

        plt.figure(figsize=(6,3.5))
        plt.bar(['Bot', 'Bookie'], [p_bot, p_book], color=[color, '#bdc3c7'])
        plt.title(f"{h} vs {a} ({sport[:10]})")
        plt.ylim(0, 100)
        
        path = f"img_{int(time.time())}_{h[:3]}.png"
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

# --- 5. RADAR "FILET DE PÊCHE" (TOUS LES SPORTS) ---
def lancer_scan_global():
    # On utilise les clés "parent" pour attraper tout le flux mondial d'un coup
    categories = ["soccer", "baseball", "basketball", "icehockey"]
    
    bot.send_message(CHAT_ID, "🌐 **Scan Global des Flux Mondiaux...**\n(Foot, Baseball, Basket, Hockey)")
    
    matchs_total = 0
    for sport_key in categories:
        try:
            # Appel API sur la catégorie globale
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
            response = requests.get(url)
            events = response.json()
            
            if isinstance(events, list) and len(events) > 0:
                # On prend les 8 prochains matchs de chaque catégorie
                for m in events[:8]:
                    matchs_total += 1
                    h, a = m['home_team'], m['away_team']
                    sport_display = m.get('sport_title', sport_key)
                    
                    for bookie in m['bookmakers'][:1]:
                        outcomes = bookie['markets'][0]['outcomes']
                        try:
                            cote = next(o['price'] for o in outcomes if o['name'] == h)
                            p_bot = calculer_stats(2.1, 1.2) # Moyenne test
                            p_book = (1/cote)*100
                            envoyer_analyse(h, a, p_bot, p_book, cote, sport_display)
                        except: continue
            time.sleep(0.5)
        except: continue
        
    if matchs_total == 0:
        bot.send_message(CHAT_ID, "⚠️ Aucun match actif trouvé pour le moment.\n(Vérifiez le quota de votre clé API Odds)")
    else:
        bot.send_message(CHAT_ID, f"🏁 **Scan terminé !**\n{matchs_total} matchs mondiaux analysés.")

# --- 6. COMMANDES ---
@bot.message_handler(commands=['scan'])
def handle_scan(message):
    lancer_scan_global()

@bot.message_handler(commands=['start', 'aide'])
def handle_start(message):
    bot.reply_to(message, "🤖 **PredictPro Full Vision**\n\n/scan : Analyse mondiale Foot, Baseball, Basket, Hockey.")

# --- 7. DÉMARRAGE ---
if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    
    print("🤖 Bot PredictPro : Démarrage en cours...")
    
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.send_message(CHAT_ID, "🚀 **Bot Prêt !**\nUtilisez /scan pour voir tout le sport mondial.")
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"🔄 Erreur : {e}. Relance...")
            time.sleep(10)
