import telebot, requests, time, os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from scipy.stats import poisson
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask('')
@app.route('/')
def home(): return "V20 Time-Flex Active"

TOKEN = "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww"
CHAT_ID = "1206877909"
API_KEY_ODDS = "3d26e46535751ecf611f0a42f083f33a"
bot = telebot.TeleBot(TOKEN)

# --- LOGIQUE D'ANALYSE ---
def generer_analyse_v20(m_h, m_a, sport, h_n, a_n, date_match):
    p_v1, p_v2, p_n = 0, 0, 0
    if sport != "basketball_nba":
        for i in range(12):
            for j in range(12):
                prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
                if i > j: p_v1 += prob
                elif i < j: p_v2 += prob
                else: p_n += prob
    else:
        p_v1 = (m_h**2) / (m_h**2 + m_a**2)
        p_v2 = 1 - p_v1
        p_n = 0.02

    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    gagnant = h_n if v1 > v2 else a_n
    total_estime = round(m_h + m_a, 1)
    dt_obj = datetime.fromisoformat(date_match.replace('Z', '+00:00'))
    heure_gmt = dt_obj.strftime("%H:%M")

    msg = (f"⏰ **COUP D'ENVOI : {heure_gmt} (GMT)**\n"
           f"🏟 **{h_n.upper()} VS {a_n.upper()}**\n\n"
           f"🏆 **VICTOIRE :** {gagnant} ({round(max(v1,v2),1)}%)\n"
           f"🛡 **V. OU NUL :** {h_n if v1 > v2 else a_n}/Nul ({round(max(v1+n,v2+n),1)}%)\n"
           f"📊 **SCORE ESTIMÉ :** {total_estime}\n"
           f"   👉 {h_n} : {round(m_h,1)} | {a_n} : {round(m_a,1)}\n\n"
           f"💎 **PRÉDICTION :**\n")
    
    if v1+n > 85 or v2+n > 85: msg += f"✅ Double Chance {h_n if v1 > v2 else a_n}/Nul"
    else: msg += f"🔥 Plus de {round(total_estime - 0.5, 1)} points/buts"

    return msg, [v1, n, v2, v1+n, v2+n]

# --- SCANNER ---
def lancer_scan_v20(sport_key, heures_limite):
    bot.send_message(CHAT_ID, f"📡 **Scan des matchs ({heures_limite}h) - {sport_key}...**")
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        
        maintenant = datetime.utcnow()
        limite_time = maintenant + timedelta(hours=int(heures_limite))
        matchs_trouves = 0

        for m in events:
            date_m = datetime.fromisoformat(m['commence_time'].replace('Z', '+00:00')).replace(tzinfo=None)
            
            if maintenant <= date_m <= limite_time:
                h, a = m['home_team'], m['away_team']
                c_h = next(o['price'] for o in m['bookmakers'][0]['markets'][0]['outcomes'] if o['name'] == h)
                c_a = next(o['price'] for o in m['bookmakers'][0]['markets'][0]['outcomes'] if o['name'] == a)
                
                if sport_key == "soccer": m_h, m_a = 1.8/c_h*3.2, 1.4/c_a*3.2
                elif sport_key == "basketball_nba": m_h, m_a = 114/c_h, 109/c_a
                elif sport_key == "icehockey_nhl": m_h, m_a = 3.6/c_h*2.2, 3.1/c_a*2.2
                else: m_h, m_a = 4.9/c_h*2, 4.3/c_a*2

                text, vals = generer_analyse_v20(m_h, m_a, sport_key, h, a, m['commence_time'])
                
                plt.figure(figsize=(6,3))
                plt.bar(['V1', 'Nul', 'V2', '1N', 'N2'], vals, color=['#3498db','#95a5a6','#e74c3c','#2ecc71','#27ae60'])
                plt.ylim(0, 100)
                path = f"v20_{int(time.time())}.png"
                plt.savefig(path); plt.close()

                with open(path, "rb") as f: bot.send_photo(CHAT_ID, f, caption=text, parse_mode='Markdown')
                matchs_trouves += 1
                time.sleep(1)
                if matchs_trouves >= 5: break 

        if matchs_trouves == 0:
            bot.send_message(CHAT_ID, f"📭 Aucun match dans les {heures_limite}h.")
    except:
        bot.send_message(CHAT_ID, "❌ Erreur API.")

# --- INTERFACE ---
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = InlineKeyboardMarkup()
    # On crée des lignes pour chaque sport avec le choix 6h ou 12h
    markup.add(InlineKeyboardButton("⚽️ Foot (6h)", callback_data="v20_soccer_6"), InlineKeyboardButton("⚽️ Foot (12h)", callback_data="v20_soccer_12"))
    markup.add(InlineKeyboardButton("🏀 NBA (6h)", callback_data="v20_basketball_nba_6"), InlineKeyboardButton("🏀 NBA (12h)", callback_data="v20_basketball_nba_12"))
    markup.add(InlineKeyboardButton("🏒 NHL (6h)", callback_data="v20_icehockey_nhl_6"), InlineKeyboardButton("🏒 NHL (12h)", callback_data="v20_icehockey_nhl_12"))
    markup.add(InlineKeyboardButton("⚾️ MLB (6h)", callback_data="v20_baseball_mlb_6"), InlineKeyboardButton("⚾️ MLB (12h)", callback_data="v20_baseball_mlb_12"))
    bot.send_message(CHAT_ID, "🏆 **PREDICTPRO V20 - FILTRE TEMPOREL**\nChoisis ton sport et l'échéance :", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if "v20_" in call.data:
        parts = call.data.split('_')
        sport = parts[1] if len(parts) == 3 else f"{parts[1]}_{parts[2]}"
        heures = parts[-1]
        lancer_scan_v20(sport, heures)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.infinity_polling()
