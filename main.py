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
def home(): return "PredictPro V9 Décisionnel est Live!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 2. MOTEUR DE COMPARAISON E1 vs E2 ---
def moteur_poisson_decision(m_dom, m_ext):
    p_v1, p_v2, p_nul = 0, 0, 0
    p_e1_05, p_e2_05 = 0, 0
    
    for i in range(0, 10):
        for j in range(0, 10):
            prob = poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
            if i > j: p_v1 += prob
            elif i < j: p_v2 += prob
            else: p_nul += prob
            
            if i >= 1: p_e1_05 += prob # Probabilité E1 marque
            if j >= 1: p_e2_05 += prob # Probabilité E2 marque

    return {
        "V1": round(p_v1 * 100, 1), "V2": round(p_v2 * 100, 1), "N": round(p_nul * 100, 1),
        "E1_05": round(p_e1_05 * 100, 1), "E2_05": round(p_e2_05 * 100, 1)
    }

# --- 3. ENVOI DE L'ANALYSE AVEC DÉCISION ---
def envoyer_alerte_v9(h, a, stats, sport):
    try:
        # LOGIQUE DE DÉCISION : Qui a le plus de chances de marquer ?
        if stats['E1_05'] >= stats['E2_05']:
            meilleur_buteur = h
            proba_buteur = stats['E1_05']
        else:
            meilleur_buteur = a
            proba_buteur = stats['E2_05']

        plt.figure(figsize=(8,5))
        labels = ['V1', 'V2', f'But {h[:5]}', f'But {a[:5]}']
        valeurs = [stats['V1'], stats['V2'], stats['E1_05'], stats['E2_05']]
        colors = ['#3498db', '#e74c3c', '#f1c40f', '#e67e22']
        
        plt.bar(labels, valeurs, color=colors)
        plt.title(f"Décision : {h} vs {a}")
        plt.ylim(0, 100)
        
        path = f"v9_{int(time.time())}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"🏟 **{h.upper()} vs {a.upper()}**\n"
               f"🏆 Sport : {sport.capitalize()}\n\n"
               f"🔥 **OPTION BUTS : {meilleur_buteur}**\n"
               f"🎯 Probabilité : {proba_buteur}%\n\n"
               f"📊 **Détails :**\n"
               f"• Victoire {h} : {stats['V1']}%\n"
               f"• Victoire {a} : {stats['V2']}%\n"
               f"• {h} marque au moins 1 but : {stats['E1_05']}%\n"
               f"• {a} marque au moins 1 but : {stats['E2_05']}%")
        
        bot.send_photo(CHAT_ID, open(path, "rb"), caption=msg, parse_mode='Markdown')
    except: pass

# --- 4. SCANNER & CALCUL DYNAMIQUE ---
def lancer_scan_v9(sport_key):
    bot.send_message(CHAT_ID, f"🧠 **Analyse comparative en cours ({sport_key})...**")
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
                    
                    # Moyennes basées sur les cotes (Indice de force)
                    base = 1.6 if sport_key == "soccer" else 4.0
                    m_h = round(base * (1/c_h) * 3.5 * 1.15, 2)
                    m_a = round(base * (1/c_a) * 3.5, 2)
                    
                    stats = moteur_poisson_decision(m_h, m_a)
                    envoyer_alerte_v9(h_name, a_name, stats, sport_key)
        else: bot.send_message(CHAT_ID, "⚠️ Pas de matchs.")
    except: bot.send_message(CHAT_ID, "❌ Erreur API.")

# --- 5. MENU & DÉMARRAGE ---
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚽️ Football", callback_data="v9_soccer"),
               InlineKeyboardButton("🏀 Basketball", callback_data="v7_basketball_nba"))
    markup.add(InlineKeyboardButton("⚾️ Baseball", callback_data="v9_baseball_mlb"),
               InlineKeyboardButton("🏒 Hockey", callback_data="v9_icehockey_nhl"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V9 - DÉCISIONNEL**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v9_"): lancer_scan_v9(call.data.replace("v9_", ""))

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    time.sleep(35)
    while True:
        try:
            bot.remove_webhook()
            bot.send_message(CHAT_ID, "✅ **Système Décisionnel V9 Prêt !**")
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(10)
