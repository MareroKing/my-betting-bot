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
def home(): return "PredictPro V16 Trader Mode est Actif !"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 2. MOTEUR DE CALCUL AVANCÉ ---
def moteur_trader(m_h, m_a, sport):
    p_v1, p_v2, p_n = 0, 0, 0
    # On simule 15 buts/points max pour la précision
    for i in range(15):
        for j in range(15):
            prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
            if i > j: p_v1 += prob
            elif i < j: p_v2 += prob
            else: p_n += prob
            
    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    dc1, dc2 = v1 + n, v2 + n
    total_estime = m_h + m_a
    
    # Choix du conseil rentable
    conseil = ""
    if dc1 > 80: conseil = "🛡 1N (Sécurité Max)"
    elif dc2 > 80: conseil = "🛡 N2 (Sécurité Max)"
    elif v1 > 65: conseil = "🔥 Victoire Domicile"
    elif v2 > 65: conseil = "🔥 Victoire Extérieur"
    else: 
        seuil = 1.5 if sport == "soccer" else 205 if sport == "basketball_nba" else 4.5
        conseil = f"📊 Over {seuil} (Probabilité Totaux)"

    return {
        "v1": round(v1, 1), "v2": round(v2, 1), "n": round(n, 1),
        "dc1": round(dc1, 1), "dc2": round(dc2, 1),
        "total": round(total_estime, 1), "conseil": conseil
    }

# --- 3. GÉNÉRATION DU GRAPHIQUE ---
def generer_graphique(h, a, stats):
    plt.figure(figsize=(8, 4))
    labels = ['Victoire Dom.', 'Nul', 'Victoire Ext.', 'Double Ch. 1N', 'Double Ch. N2']
    valeurs = [stats['v1'], stats['n'], stats['v2'], stats['dc1'], stats['dc2']]
    couleurs = ['#3498db', '#95a5a6', '#e74c3c', '#2ecc71', '#27ae60']
    
    plt.barh(labels, valeurs, color=couleurs)
    plt.xlim(0, 100)
    plt.title(f"Analyse Probabilités : {h} vs {a}")
    for index, value in enumerate(valeurs):
        plt.text(value, index, f" {value}%", va='center', fontweight='bold')
    
    path = f"plot_{int(time.time())}.png"
    plt.savefig(path)
    plt.close()
    return path

# --- 4. SCANNER ---
def lancer_scan_v16(sport_key):
    bot.send_message(CHAT_ID, f"📊 **Analyse Trader en cours ({sport_key.upper()})...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        
        for m in events[:5]:
            h, a = m['home_team'], m['away_team']
            outcomes = m['bookmakers'][0]['markets'][0]['outcomes']
            c_h = next(o['price'] for o in outcomes if o['name'] == h)
            c_a = next(o['price'] for o in outcomes if o['name'] == a)
            
            # Calcul des moyennes dynamiques (Lambda)
            # On utilise les cotes pour "deviner" la forme des équipes
            base = 1.8 if sport_key == "soccer" else 115 if sport_key == "basketball_nba" else 3.5
            m_h = (base / c_h) * 1.15 # Avantage domicile
            m_a = (base / c_a)
            
            stats = moteur_trader(m_h, m_a, sport_key)
            img_path = generer_graphique(h, a, stats)
            
            msg = (f"🏟 **{h.upper()} vs {a.upper()}**\n\n"
                   f"📈 **Victoire :** {h} {stats['v1']}% | {a} {stats['v2']}% (Nul: {stats['n']}%)\n"
                   f"🛡 **Double Chance :** 1N {stats['dc1']}% | N2 {stats['dc2']}%\n"
                   f"📊 **Totaux attendus :** {stats['total']}\n\n"
                   f"💎 **CONSEIL RENTABLE :**\n"
                   f"👉 `{stats['conseil']}`")
            
            with open(img_path, "rb") as photo:
                bot.send_photo(CHAT_ID, photo, caption=msg, parse_mode='Markdown')
            time.sleep(1)
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Erreur : {str(e)}")

# --- 5. INTERFACE ---
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("⚽️ Football", callback_data="v16_soccer"),
        InlineKeyboardButton("🏀 NBA", callback_data="v16_basketball_nba"),
        InlineKeyboardButton("🏒 NHL", callback_data="v16_icehockey_nhl"),
        InlineKeyboardButton("⚾️ MLB", callback_data="v16_baseball_mlb")
    )
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V16 - TRADER PRO**\nChoisissez votre marché :", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v16_"):
        lancer_scan_v16(call.data.replace("v16_", ""))

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(5)
