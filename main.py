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
def home(): return "PredictPro V13 Intégrale est Actif !"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 2. MOTEUR UNIFIÉ (VAINQUEUR + TES OPTIONS) ---

def calculer_stats(m_h, m_a, sport):
    p_v1, p_v2, p_n = 0, 0, 0
    p_opt1, p_opt2 = 0, 0 # Options personnalisées selon le sport
    
    # Loi de Poisson pour les probabilités de base
    limit = 12 if sport != "basketball_nba" else 150
    for i in range(12):
        for j in range(12):
            prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
            if i > j: p_v1 += prob
            elif i < j: p_v2 += prob
            else: p_n += prob
            
            # Application de tes "gouts" (Over/Under)
            if sport == "soccer" and (i+j) > 1.5: p_opt1 += prob
            if sport == "icehockey_nhl":
                if (i+j) > 4.5: p_opt1 += prob
                if (i+j) < 8.5: p_opt2 += prob
            if sport == "baseball_mlb":
                if (i+j) > 7.5: p_opt1 += prob
                if (i+j) < 12.5: p_opt2 += prob

    # Cas particulier NBA (Calcul probabiliste direct)
    if sport == "basketball_nba":
        p_v1 = 100 / (1 + (m_a/m_h)**8)
        p_v2 = 100 - p_v1
        return {"v1":round(p_v1,1), "v2":round(p_v2,1), "1n":round(p_v1,1), "n2":round(p_v2,1), "opt1":95.0, "opt2":70.0}

    return {
        "v1": round(p_v1*100, 1), "v2": round(p_v2*100, 1), "n": round(p_n*100, 1),
        "1n": round((p_v1 + p_n)*100, 1), "n2": round((p_v2 + p_n)*100, 1),
        "opt1": round(p_opt1*100, 1), "opt2": round(p_opt2*100, 1)
    }

# --- 3. SCANNER ---

def executer_scan_v13(sport_key):
    bot.send_message(CHAT_ID, f"📡 **Analyse Expert {sport_key.upper()} en cours...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        
        for m in events[:5]:
            h, a = m['home_team'], m['away_team']
            outcomes = m['bookmakers'][0]['markets'][0]['outcomes']
            c_h = next(o['price'] for o in outcomes if o['name'] == h)
            c_a = next(o['price'] for o in outcomes if o['name'] == a)
            
            # Ajustement des moyennes de force (Lambda)
            m_h = 1.7*(1/c_h)*3.2 if sport_key=="soccer" else 4.2*(1/c_h)*2.5
            m_a = 1.3*(1/c_a)*3.2 if sport_key=="soccer" else 3.7*(1/c_a)*2.5
            
            stats = calculer_stats(m_h, m_a, sport_key)
            fav = h if c_h < c_a else a

            msg = (f"🏟 **{h} vs {a}**\n"
                   f"⭐ **Favori : {fav}**\n\n"
                   f"✅ **RÉSULTAT :**\n"
                   f"• Victoire {h} : {stats['v1']}%\n"
                   f"• Victoire {a} : {stats['v2']}%\n\n"
                   f"🛡 **SÉCURITÉ :**\n"
                   f"• 1N (Home ou Nul) : {stats['1n']}%\n"
                   f"• N2 (Away ou Nul) : {stats['n2']}%\n\n"
                   f"📊 **TES OPTIONS :**\n")

            if sport_key == "soccer": msg += f"🔥 Over 1.5 Buts : {stats['opt1']}%"
            elif sport_key == "basketball_nba": msg += f"🏀 +200 Pts : {stats['opt1']}%\n🎯 {fav} > 100 Pts : {stats['opt2']}%"
            elif sport_key == "icehockey_nhl": msg += f"🏒 Over 4.5 : {stats['opt1']}%\n🛡 Under 8.5 : {stats['opt2']}%"
            elif sport_key == "baseball_mlb": msg += f"⚾️ Over 7.5 : {stats['opt1']}%\n🛡 Under 12.5 : {stats['opt2']}%"

            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            time.sleep(1)
    except: bot.send_message(CHAT_ID, "❌ Erreur de scan.")

# --- 4. INTERFACE ---

@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚽️ Foot (1N2 + O1.5)", callback_data="v13_soccer"))
    markup.add(InlineKeyboardButton("🏀 NBA (Win + 200pts)", callback_data="v13_basketball_nba"))
    markup.add(InlineKeyboardButton("🏒 NHL (Win + 4.5/8.5)", callback_data="v13_icehockey_nhl"))
    markup.add(InlineKeyboardButton("⚾️ MLB (Win + 7.5/12.5)", callback_data="v13_baseball_mlb"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V13 - VAINQUEURS & OPTIONS**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v13_"):
        executer_scan_v13(call.data.replace("v13_", ""))

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(5)
