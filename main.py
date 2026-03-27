import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
import os
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. CONFIGURATION DU SERVEUR ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro V10.2 Silent is Active!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. PARAMÈTRES ---
TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 3. FONCTION ANTI-SOMMEIL (SILENCIEUSE) ---
def keep_alive_ping():
    """Envoie un ping à l'URL de Render pour éviter la mise en veille"""
    url = "https://bet-bot-free-0aw4.onrender.com"
    while True:
        try:
            requests.get(url)
            # On logue uniquement dans la console Render, pas sur Telegram
            print("📡 Ping de survie envoyé à Render...")
        except:
            print("📡 Échec du ping de survie")
        time.sleep(600) # Toutes les 10 minutes

# --- 4. CALCULS & INTELLIGENCE ---
def obtenir_etoiles(stats):
    score = 0
    diff_v = abs(stats['V1'] - stats['V2'])
    if diff_v > 40: score += 2
    elif diff_v > 20: score += 1
    max_off = max(stats['E1_05'], stats['E2_05'])
    if max_off > 90: score += 2
    elif max_off > 85: score += 1
    max_dc = max(stats['1N'], stats['N2'])
    if max_dc > 88: score += 1
    
    if score >= 5: return "⭐⭐⭐⭐⭐ (ÉLITE)"
    if score == 4: return "⭐⭐⭐⭐ (TRÈS FORT)"
    if score == 3: return "⭐⭐⭐ (SOLIDE)"
    return "⭐⭐ (À SURVEILLER)"

def moteur_v10(m_dom, m_ext):
    p_v1, p_v2, p_nul = 0, 0, 0
    p_e1_05, p_e2_05 = 0, 0
    for i in range(0, 10):
        for j in range(0, 10):
            prob = poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
            if i > j: p_v1 += prob
            elif i < j: p_v2 += prob
            else: p_nul += prob
            if i >= 1: p_e1_05 += prob
            if j >= 1: p_e2_05 += prob
    return {
        "V1": round(p_v1 * 100, 1), "V2": round(p_v2 * 100, 1), "N": round(p_nul * 100, 1),
        "1N": round((p_v1 + p_nul) * 100, 1), "N2": round((p_v2 + p_nul) * 100, 1),
        "E1_05": round(p_e1_05 * 100, 1), "E2_05": round(p_e2_05 * 100, 1)
    }

# --- 5. INTERFACE & SCAN ---
def envoyer_alerte_v10(h, a, stats, sport):
    try:
        etoiles = obtenir_etoiles(stats)
        option_but = h if stats['E1_05'] >= stats['E2_05'] else a
        plt.figure(figsize=(8,5))
        plt.bar(['V1', 'V2', '1N', 'N2'], [stats['V1'], stats['V2'], stats['1N'], stats['N2']], color=['#3498db', '#e74c3c', '#2ecc71', '#27ae60'])
        plt.title(f"{h} vs {a}")
        plt.ylim(0, 100)
        path = f"v10_{int(time.time())}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"💎 **CONFIANCE : {etoiles}**\n\n"
               f"🏟 **{h} vs {a}**\n"
               f"🎯 **OPTION BUT : {option_but} ({max(stats['E1_05'], stats['E2_05'])}%)**\n\n"
               f"📊 **Détails :**\n"
               f"V1: {stats['V1']}% | V2: {stats['V2']}% | DC: {max(stats['1N'], stats['N2'])}%")
        
        bot.send_photo(CHAT_ID, open(path, "rb"), caption=msg, parse_mode='Markdown')
    except: pass

def lancer_scan_v10(sport_key):
    bot.send_message(CHAT_ID, f"🔎 **Analyse {sport_key.upper()} demandée...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        if isinstance(events, list) and len(events) > 0:
            for m in events[:5]:
                h_n, a_n = m['home_team'], m['away_team']
                for bookie in m['bookmakers'][:1]:
                    outcomes = bookie['markets'][0]['outcomes']
                    c_h = next(o['price'] for o in outcomes if o['name'] == h_n)
                    c_a = next(o['price'] for o in outcomes if o['name'] == a_n)
                    base = 1.6 if sport_key == "soccer" else 4.0
                    m_h, m_a = round(base * (1/c_h) * 3.5 * 1.15, 2), round(base * (1/c_a) * 3.5, 2)
                    stats = moteur_v10(m_h, m_a)
                    envoyer_alerte_v10(h_n, a_n, stats, sport_key)
        else: bot.send_message(CHAT_ID, "⚠️ Pas de matchs.")
    except: bot.send_message(CHAT_ID, "❌ Erreur API.")

# --- 6. GESTION DES COMMANDES ---
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚽️ Foot", callback_data="v10_soccer"),
               InlineKeyboardButton("🏀 Basket", callback_data="v10_basketball_nba"))
    markup.add(InlineKeyboardButton("⚾️ Baseball", callback_data="v10_baseball_mlb"),
               InlineKeyboardButton("🏒 Hockey", callback_data="v10_icehockey_nhl"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V10.2**\nCliquez sur un sport pour analyser :", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v10_"):
        lancer_scan_v10(call.data.replace("v10_", ""))

# --- 7. DÉMARRAGE ---
if __name__ == "__main__":
    # Lancement du serveur Web et du Ping de survie
    Thread(target=run, daemon=True).start()
    Thread(target=keep_alive_ping, daemon=True).start()
    
    # Silence au démarrage (on n'envoie plus de message "Système Prêt")
    while True:
        try:
            bot.remove_webhook()
            # On logue le démarrage uniquement dans la console Render
            print("🤖 Bot PredictPro V10.2 opérationnel (Mode Silencieux)")
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(10)
