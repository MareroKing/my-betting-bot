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
def home(): return "PredictPro V8 Data-Intelligence Live!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 2. MOTEUR D'INTELLIGENCE (FORME & H2H) ---
def calculer_moyennes_dynamiques(cote_h, cote_a, sport):
    """
    Déduit la puissance d'attaque (Lambda) en fonction des cotes 
    et de l'avantage du terrain.
    """
    # Base selon le sport
    base = 1.6 if sport == "soccer" else 4.0
    
    # Plus la cote est basse, plus l'équipe est jugée "en forme" par le marché
    # On ajoute un bonus de 15% à l'équipe à domicile (Home Advantage)
    power_h = (1 / cote_h) * 3.5 * 1.15 
    power_a = (1 / cote_a) * 3.5
    
    return round(base * power_h, 2), round(base * power_a, 2)

def moteur_poisson_pro(m_dom, m_ext):
    p_v1, p_v2, p_nul = 0, 0, 0
    p_over_15, p_e1_05 = 0, 0
    
    for i in range(0, 10):
        for j in range(0, 10):
            prob = poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
            if i > j: p_v1 += prob
            elif i < j: p_v2 += prob
            else: p_nul += prob
            
            if (i + j) > 1.5: p_over_15 += prob
            if i >= 1: p_e1_05 += prob

    return {
        "V1": round(p_v1 * 100, 1), "V2": round(p_v2 * 100, 1), "N": round(p_nul * 100, 1),
        "1N": round((p_v1 + p_nul) * 100, 1), "N2": round((p_v2 + p_nul) * 100, 1),
        "O15": round(p_over_15 * 100, 1), "E1_05": round(p_e1_05 * 100, 1)
    }

# --- 3. ENVOI DE L'ANALYSE ---
def envoyer_alerte_v8(h, a, stats, sport):
    try:
        favori = h if stats['V1'] > stats['V2'] else a
        plt.figure(figsize=(8,5))
        labels = ['V1', 'V2', '1N', 'N2', 'Tot. +1.5', 'E1 +0.5']
        valeurs = [stats['V1'], stats['V2'], stats['1N'], stats['N2'], stats['O15'], stats['E1_05']]
        
        plt.bar(labels, valeurs, color=['#3498db', '#e74c3c', '#2ecc71', '#27ae60', '#f1c40f', '#e67e22'])
        plt.title(f"Intelligence Data : {h} vs {a}")
        plt.ylim(0, 100)
        
        path = f"v8_{int(time.time())}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"🏟 **{h.upper()} vs {a.upper()}**\n"
               f"📊 **PRONOSTIC : {favori}**\n\n"
               f"🔹 **Victoire :** V1:{stats['V1']}% | V2:{stats['V2']}% | N:{stats['N']}%\n"
               f"🛡 **Sécurité :** 1N:{stats['1N']}% | N2:{stats['N2']}%\n"
               f"⚽️ **Buts :** Total +1.5:{stats['O15']}% | {h} marque:{stats['E1_05']}%")
        
        bot.send_photo(CHAT_ID, open(path, "rb"), caption=msg, parse_mode='Markdown')
    except: pass

# --- 4. SCANNER ---
def lancer_scan_v8(sport_key):
    bot.send_message(CHAT_ID, f"🧠 **Analyse des performances et cotes : {sport_key}...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        if isinstance(events, list) and len(events) > 0:
            for m in events[:5]:
                h_name, a_name = m['home_team'], m['away_team']
                for bookie in m['bookmakers'][:1]:
                    outcomes = bookie['markets'][0]['outcomes']
                    c_h = next(o['price'] for o in outcomes if o['name'] == h_name)
                    c_a = next(o['price'] for o in outcomes if o['name'] == a_name)
                    
                    # On calcule les moyennes dynamiques
                    m_h, m_a = calculer_moyennes_dynamiques(c_h, c_a, sport_key)
                    stats = moteur_poisson_pro(m_h, m_a)
                    envoyer_alerte_v8(h_name, a_name, stats, sport_key)
        else: bot.send_message(CHAT_ID, "⚠️ Pas de matchs majeurs.")
    except: bot.send_message(CHAT_ID, "❌ Erreur API.")

# --- 5. MENU ---
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚽️ Foot Expert", callback_data="v8_soccer"),
               InlineKeyboardButton("🏀 Basket NBA", callback_data="v8_basketball_nba"))
    markup.add(InlineKeyboardButton("⚾️ Baseball MLB", callback_data="v8_baseball_mlb"),
               InlineKeyboardButton("🏒 Hockey NHL", callback_data="v8_icehockey_nhl"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V8 - INTELLIGENCE**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v8_"): lancer_scan_v8(call.data.replace("v8_", ""))

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    time.sleep(30)
    while True:
        try:
            bot.remove_webhook()
            bot.send_message(CHAT_ID, "✅ **Système V8 Opérationnel !**")
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(10)
