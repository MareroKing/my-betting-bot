import telebot
import requests
from scipy.stats import poisson
import time
import os
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. CONFIGURATION ---
app = Flask('')
@app.get('/')
def home(): return "PredictPro V15 Tipster Mode Actif !"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 2. LOGIQUE DE DÉCISION DU TIPSTER ---

def generer_analyse_expert(m_h, m_a, sport, h_name, a_name):
    p_v1, p_v2, p_n = 0, 0, 0
    # Simulation de Poisson pour les probabilités
    for i in range(15):
        for j in range(15):
            prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
            if i > j: p_v1 += prob
            elif i < j: p_v2 += prob
            else: p_n += prob
    
    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    dc1, dc2 = v1 + n, v2 + n
    total_estime = m_h + m_a

    # --- CHOIX DE LA PRÉDICTION À JOUER ---
    # On cherche l'option la plus sûre (> 75%)
    prediction_jouer = ""
    if dc1 > 82: prediction_jouer = f"🛡 Double Chance : {h_name} ou Nul"
    elif dc2 > 82: prediction_jouer = f"🛡 Double Chance : {a_name} ou Nul"
    elif v1 > 65: prediction_jouer = f"🔥 Victoire Directe : {h_name}"
    elif v2 > 65: prediction_jouer = f"🔥 Victoire Directe : {a_name}"
    else:
        # Si le vainqueur est incertain, on joue les totaux
        if sport == "soccer":
            prediction_jouer = "⚽️ Plus de 1.5 Buts" if total_estime > 1.8 else "⚽️ Moins de 3.5 Buts"
        elif sport == "basketball_nba":
            prediction_jouer = "🏀 Plus de 210.5 Points"
        elif sport == "icehockey_nhl":
            prediction_jouer = "🏒 Plus de 4.5 Buts"
        else:
            prediction_jouer = "⚾️ Plus de 7.5 Runs"

    return {
        "victoire": f"{h_name}: {round(v1,1)}% | {a_name}: {round(v2,1)}%",
        "vn": f"1N: {round(dc1,1)}% | N2: {round(dc2,1)}%",
        "totaux": f"Estimation : {round(total_estime, 1)}",
        "conseil": prediction_jouer
    }

# --- 3. SCANNER ---

def lancer_scan_v15(sport_key):
    bot.send_message(CHAT_ID, f"📑 **Génération du rapport {sport_key.upper()}...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        
        for m in events[:5]:
            h, a = m['home_team'], m['away_team']
            outcomes = m['bookmakers'][0]['markets'][0]['outcomes']
            c_h = next(o['price'] for o in outcomes if o['name'] == h)
            c_a = next(o['price'] for o in outcomes if o['name'] == a)
            
            # Calcul des espérances (Moyennes de points/buts)
            coef = 2.8 if sport_key == "soccer" else 1.0
            m_h = (1.8 / c_h) * coef if sport_key == "soccer" else 115 / c_h if sport_key == "basketball_nba" else 3.5 / c_h
            m_a = (1.4 / c_a) * coef if sport_key == "soccer" else 110 / c_a if sport_key == "basketball_nba" else 3.0 / c_a
            
            res = generer_analyse_expert(m_h, m_a, sport_key, h, a)

            msg = (f"🏟 **{h.upper()} VS {a.upper()}**\n\n"
                   f"🔹 **Victoire :** {res['victoire']}\n"
                   f"🛡 **Victoire ou Nul :** {res['vn']}\n"
                   f"📊 **Totaux :** {res['totaux']}\n\n"
                   f"💎 **PRÉDICTION À JOUER :**\n"
                   f"👉 `{res['conseil']}`")

            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            time.sleep(1)
    except: bot.send_message(CHAT_ID, "❌ Erreur lors de la génération du rapport.")

# --- 4. INTERFACE ---

@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚽️ Football", callback_data="v15_soccer"),
               InlineKeyboardButton("🏀 Basket NBA", callback_data="v15_basketball_nba"))
    markup.add(InlineKeyboardButton("🏒 Hockey NHL", callback_data="v15_icehockey_nhl"),
               InlineKeyboardButton("⚾️ Baseball MLB", callback_data="v15_baseball_mlb"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V15 - MODE TIPSTER**\nChoisissez un sport pour obtenir le pronostic final :", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v15_"):
        lancer_scan_v15(call.data.replace("v15_", ""))

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(5)
