import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
import os
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. CONFIGURATION DU SERVEUR (POUR RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "PredictPro V6.1 Ultra-Intelligence est en ligne !"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. CONFIGURATION DU BOT ---
TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- 3. MOTEUR DE CALCUL EXPERT ---
def analyser_match_complet(m_dom, m_ext):
    p_win, p_over25, p_handicap_plus = 0, 0, 0
    for i in range(0, 8):
        for j in range(0, 8):
            prob = poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
            if i > j: p_win += prob
            if (i + j) > 2.5: p_over25 += prob
            if (i + 1.5) > j: p_handicap_plus += prob
    return {
        "victoire": round(p_win * 100, 1),
        "over25": round(p_over25 * 100, 1),
        "handicap": round(p_handicap_plus * 100, 1)
    }

# --- 4. ENVOI DES ALERTES ---
def envoyer_alerte_expert(h, a, stats, sport):
    try:
        plt.figure(figsize=(7,4))
        labels = ['Victoire', 'Over 2.5', 'H+1.5']
        valeurs = [stats['victoire'], stats['over25'], stats['handicap']]
        plt.bar(labels, valeurs, color=['#3498db', '#9b59b6', '#2ecc71'])
        plt.title(f"Analyse Expert : {h} vs {a}")
        plt.ylim(0, 100)
        
        path = f"expert_{int(time.time())}.png"
        plt.savefig(path)
        plt.close()
        
        msg = (f"🧐 **ANALYSE EXPERT : {sport.upper()}**\n\n"
               f"🏟 **{h} vs {a}**\n\n"
               f"🔵 Victoire : {stats['victoire']}%\n"
               f"🟣 Over 2.5 : {stats['over25']}%\n"
               f"🟢 Handicap (+1.5) : {stats['handicap']}%")
        
        bot.send_photo(CHAT_ID, open(path, "rb"), caption=msg, parse_mode='Markdown')
    except: pass

# --- 5. LOGIQUE DE SCAN ---
def lancer_scan_expert(sport_key):
    bot.send_message(CHAT_ID, f"🧠 **Analyse en cours sur {sport_key}...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        if isinstance(events, list) and len(events) > 0:
            for m in events[:5]:
                # On ajuste les moyennes selon le sport (Soccer vs Baseball)
                m_dom = 1.8 if sport_key == "soccer" else 4.2
                m_ext = 1.2 if sport_key == "soccer" else 3.5
                stats = analyser_match_complet(m_dom, m_ext)
                envoyer_alerte_expert(m['home_team'], m['away_team'], stats, sport_key)
        else:
            bot.send_message(CHAT_ID, "⚠️ Aucun match trouvé actuellement.")
    except:
        bot.send_message(CHAT_ID, "❌ Erreur API.")

# --- 6. INTERFACE BOUTONS ---
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup
