import telebot, requests, time, os
import matplotlib.pyplot as plt
from scipy.stats import poisson
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask('')
@app.route('/')
def home(): return "V18 Online"

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

def generer_analyse(m_h, m_a, sport, h_n, a_n):
    # Calcul des probabilités de base
    p_v1, p_v2, p_n = 0, 0, 0
    if sport != "basketball_nba":
        for i in range(12):
            for j in range(12):
                prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
                if i > j: p_v1 += prob
                elif i < j: p_v2 += prob
                else: p_n += prob
    else: # Logique spéciale Basket (Scores 100+)
        p_v1 = (m_h**2) / (m_h**2 + m_a**2)
        p_v2 = 1 - p_v1
        p_n = 0.02 # Match nul rarissime

    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    
    # Choix de l'équipe gagnante
    gagnant = h_n if v1 > v2 else a_n
    confiance_gagnant = max(v1, v2)

    # Prédiction Totaux
    total_match = round(m_h + m_a, 1)
    unite = "Buts" if sport in ["soccer", "icehockey_nhl"] else "Points" if sport == "basketball_nba" else "Runs"

    # Message structuré
    msg = (f"🏟 **{h_n.upper()} VS {a_n.upper()}**\n\n"
           f"🏆 **VICTOIRE :** {gagnant} ({round(confiance_gagnant,1)}%)\n"
           f"🛡 **V. OU NUL :** {h_n if v1 > v2 else a_n} ou Nul ({round(max(v1+n, v2+n),1)}%)\n"
           f"📊 **SCORE ATTENDU :** {total_match} {unite}\n"
           f"   👉 {h_n} : {round(m_h,1)}\n"
           f"   👉 {a_n} : {round(m_a,1)}\n\n"
           f"💎 **PRONO À JOUER :**\n")
    
    if v1+n > 85 or v2+n > 85: msg += f"✅ Double Chance {h_n if v1 > v2 else a_n}/Nul"
    else: msg += f"🔥 Plus de {round(total_match - 1, 0.5 if sport=='soccer' else 1)} {unite}"

    return msg, [v1, n, v2, v1+n, v2+n]

def lancer_scan_v18(sport_key):
    bot.send_message(CHAT_ID, f"🧠 **Analyse experte {sport_key}...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        for m in events[:4]:
            h, a = m['home_team'], m['away_team']
            c_h = next(o['price'] for o in m['bookmakers'][0]['markets'][0]['outcomes'] if o['name'] == h)
            c_a = next(o['price'] for o in m['bookmakers'][0]['markets'][0]['outcomes'] if o['name'] == a)
            
            # Ajustement des puissances réelles
            if sport_key == "soccer": m_h, m_a = 1.8/c_h*3, 1.4/c_a*3
            elif sport_key == "basketball_nba": m_h, m_a = 115/c_h, 110/c_a
            elif sport_key == "icehockey_nhl": m_h, m_a = 3.5/c_h*2.2, 3.0/c_a*2.2
            else: m_h, m_a = 4.8/c_h*2, 4.2/c_a*2

            text, vals = generer_analyse(m_h, m_a, sport_key, h, a)
            
            # Graphique corrigé
            plt.figure(figsize=(6,3))
            plt.bar(['V1', 'Nul', 'V2', '1N', 'N2'], vals, color=['#3498db','#95a5a6','#e74c3c','#2ecc71','#27ae60'])
            plt.ylim(0, 100)
            plt.title(f"{h} vs {a}")
            path = f"v18_{int(time.time())}.png"
            plt.savefig(path); plt.close()

            with open(path, "rb") as f: bot.send_photo(CHAT_ID, f, caption=text, parse_mode='Markdown')
            time.sleep(1)
    except: bot.send_message(CHAT_ID, "❌ Erreur scan.")

@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚽️ Foot Expert", callback_data="v18_soccer"),
               InlineKeyboardButton("🏀 NBA Expert", callback_data="v18_basketball_nba"))
    markup.add(InlineKeyboardButton("🏒 NHL Expert", callback_data="v18_icehockey_nhl"),
               InlineKeyboardButton("⚾️ MLB Expert", callback_data="v18_baseball_mlb"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V18 - MODE EXPERT**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("v18_"): lancer_scan_v18(call.data.replace("v18_", ""))

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    while True:
        try: bot.infinity_polling()
        except: time.sleep(5)
