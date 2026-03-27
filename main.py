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
def home(): return "PredictPro V17 Expert Selection est Actif !"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 2. MOTEUR DE CALCUL ---
def calculer_pépites(m_h, m_a, c_h, c_a):
    p_v1, p_v2, p_n = 0, 0, 0
    for i in range(15):
        for j in range(15):
            prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
            if i > j: p_v1 += prob
            elif i < j: p_v2 += prob
            else: p_n += prob
    
    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    dc1, dc2 = v1 + n, v2 + n
    
    # On retourne la probabilité la plus haute pour le tri
    score_max = max(v1, v2, dc1, dc2)
    return {
        "v1": round(v1, 1), "v2": round(v2, 1), "n": round(n, 1),
        "dc1": round(dc1, 1), "dc2": round(dc2, 1),
        "score_max": score_max, "total": round(m_h + m_a, 1)
    }

# --- 3. GÉNÉRATION DU GRAPHIQUE ---
def generer_graphique(h, a, stats):
    plt.figure(figsize=(8, 4))
    labels = ['V1', 'Nul', 'V2', '1N', 'N2']
    valeurs = [stats['v1'], stats['n'], stats['v2'], stats['dc1'], stats['dc2']]
    couleurs = ['#3498db', '#95a5a6', '#e74c3c', '#2ecc71', '#27ae60']
    plt.barh(labels, valeurs, color=couleurs)
    plt.xlim(0, 100)
    plt.title(f"TOP SÉLECTION : {h} vs {a}")
    for i, v in enumerate(valeurs):
        plt.text(v + 1, i, f"{v}%", va='center', fontweight='bold')
    path = f"top_{int(time.time())}.png"
    plt.savefig(path)
    plt.close()
    return path

# --- 4. SCANNER DE PÉPITES ---
def lancer_scan_pépites(sport_key):
    bot.send_message(CHAT_ID, f"🔦 **Recherche des 4 meilleures opportunités ({sport_key.upper()})...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        
        analyses = []
        for m in events:
            h, a = m['home_team'], m['away_team']
            outcomes = m['bookmakers'][0]['markets'][0]['outcomes']
            c_h = next(o['price'] for o in outcomes if o['name'] == h)
            c_a = next(o['price'] for o in outcomes if o['name'] == a)
            
            base = 1.8 if sport_key == "soccer" else 115 if sport_key == "basketball_nba" else 3.5
            m_h, m_a = (base / c_h) * 1.15, (base / c_a)
            stats = calculer_pépites(m_h, m_a, c_h, c_a)
            
            analyses.append({"h": h, "a": a, "stats": stats, "c_h": c_h, "c_a": c_a})

        # --- TRI PAR SCORE DE CONFIANCE (DÉCROISSANT) ---
        analyses = sorted(analyses, key=lambda x: x['stats']['score_max'], reverse=True)

        # On ne garde que les 4 meilleurs
        for item in analyses[:4]:
            stats = item['stats']
            img = generer_graphique(item['h'], item['a'], stats)
            
            # Choix automatique de l'événement évident
            conseil = ""
            if stats['v1'] > 70: conseil = f"🔥 VICTOIRE ÉVIDENTE : {item['h']}"
            elif stats['v2'] > 70: conseil = f"🔥 VICTOIRE ÉVIDENTE : {item['a']}"
            elif stats['dc1'] > 85: conseil = f"🛡 SÉCURITÉ : {item['h']} ou Nul"
            elif stats['dc2'] > 85: conseil = f"🛡 SÉCURITÉ : {item['a']} ou Nul"
            else: conseil = f"📊 TOTAL ATTENDU : {stats['total']}"

            msg = (f"🏟 **{item['h'].upper()} vs {item['a'].upper()}**\n"
                   f"💰 Cote : {item['c_h']} | {item['c_a']}\n\n"
                   f"💎 **ÉVÉNEMENT ÉVIDENT :**\n"
                   f"👉 `{conseil}`")
            
            with open(img, "rb") as photo:
                bot.send_photo(CHAT_ID, photo, caption=msg, parse_mode='Markdown')
            time.sleep(1)
            
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Erreur : {str(e)}")

# --- 5. INTERFACE ---
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚽️ Top Foot", callback_data="v17_soccer"),
               InlineKeyboardButton("🏀 Top NBA", callback_data="v17_basketball_nba"))
    markup.add(InlineKeyboardButton("🏒 Top NHL", callback_data="v17_icehockey_nhl"),
               InlineKeyboardButton("⚾️ Top MLB", callback_data="v17_baseball_mlb"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V17 - TOP SÉLECTION**\nLe bot ne sortira que les 4 matchs les plus sûrs :", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v17_"):
        lancer_scan_pépites(call.data.replace("v17_", ""))

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(5)
