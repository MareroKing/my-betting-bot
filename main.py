import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
import os
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. CONFIGURATION ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro V5 Interactif est en ligne !"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 2. INTELLIGENCE DYNAMIQUE (SIMULATION DE FORME) ---
def estimer_moyenne_buts(sport):
    """Ajuste les moyennes de Poisson selon le sport pour plus de réalisme"""
    stats = {
        "Soccer": (1.6, 1.1),
        "Baseball": (4.5, 3.8),
        "Basketball": (110, 105),
        "Ice Hockey": (3.2, 2.5)
    }
    return stats.get(sport, (2.0, 1.5))

def calculer_stats_pro(m_dom, m_ext):
    p_win = 0
    # Pour les gros scores (Basket), on utilise une approximation simple
    if m_dom > 50:
        return 55.0 # Estimation fixe pour les sports à haut score sans API de stats
    for i in range(1, 10):
        for j in range(0, i):
            p_win += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_win * 100, 1)

# --- 3. INTERFACE À BOUTONS ---
def menu_principal():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("⚽️ Foot", callback_data="scan_soccer"),
        InlineKeyboardButton("⚾️ MLB", callback_data="scan_baseball"),
        InlineKeyboardButton("🏀 Basket", callback_data="scan_basketball"),
        InlineKeyboardButton("🏒 Hockey", callback_data="scan_icehockey")
    )
    return markup

# --- 4. ENVOI DE L'ANALYSE ---
def envoyer_analyse(h, a, p_bot, p_book, cote, sport):
    try:
        value = p_bot - p_book
        icon = "✅" if value > 3 else "🔴"
        color = "#27ae60" if value > 3 else "#e74c3c"
        
        plt.figure(figsize=(6,3.5))
        plt.bar(['PredictPro', 'Marché'], [p_bot, p_book], color=[color, '#bdc3c7'])
        plt.title(f"{h} vs {a}")
        plt.ylim(0, 100)
        
        path = f"img_{int(time.time())}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"{icon} **ANALYSE {sport.upper()}**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"📈 Cote : {cote}\n"
               f"📊 Proba : {p_bot}%\n"
               f"💰 Value : {round(value, 1)}%")
        
        bot.send_photo(CHAT_ID, open(path, "rb"), caption=msg, parse_mode='Markdown')
    except: pass

# --- 5. MOTEUR DE SCAN FILTRÉ ---
def lancer_scan_specifique(sport_key):
    bot.send_message(CHAT_ID, f"🔎 **Scan ciblé sur {sport_key.upper()}...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        
        if isinstance(events, list) and len(events) > 0:
            m_dom, m_ext = estimer_moyenne_buts(sport_key.capitalize())
            for m in events[:6]:
                h = m['home_team']
                for bookie in m['bookmakers'][:1]:
                    outcomes = bookie['markets'][0]['outcomes']
                    cote = next(o['price'] for o in outcomes if o['name'] == h)
                    p_bot = calculer_stats_pro(m_dom, m_ext)
                    p_book = (1/cote)*100
                    envoyer_analyse(h, m['away_team'], p_bot, p_book, cote, sport_key)
        else:
            bot.send_message(CHAT_ID, "⚠️ Aucun match disponible pour ce sport.")
    except:
        bot.send_message(CHAT_ID, "❌ Erreur de connexion API.")

# --- 6. GESTIONNAIRES DE COMMANDES ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.reply_to(message, "🚀 **Tableau de Bord PredictPro**\nChoisissez un sport à analyser :", reply_markup=menu_principal())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("scan_"):
        sport = call.data.replace("scan_", "")
        lancer_scan_specifique(sport)

# --- 7. DÉMARRAGE ---
if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            bot.send_message(CHAT_ID, "⚡️ **PredictPro V5 Prêt !**\nTapez /menu pour afficher les options.", reply_markup=menu_principal())
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(10)
