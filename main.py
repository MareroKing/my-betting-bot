import telebot, requests, time, os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from scipy.stats import poisson
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww")
CHAT_ID = os.getenv("CHAT_ID", "1206877909")
API_KEY_ODDS = os.getenv("ODDS_API_KEY", "3d26e46535751ecf611f0a42f083f33a")

app = Flask('')
@app.route('/')
def home(): return "PredictPro V20 + Stats Score Active"

bot = telebot.TeleBot(TOKEN)

# --- CONFIGURATION DES LIGUES ---
SPORTS_DATA = {
    "⚽ FOOTBALL": {
        "🇫🇷 Ligue 1": "soccer_france_ligue_one", "🇪🇸 La Liga": "soccer_spain_la_liga",
        "🇬🇧 Premier League": "soccer_epl", "🇮🇹 Serie A": "soccer_italy_serie_a",
        "🇩🇪 Bundesliga": "soccer_germany_bundesliga", "🌍 Autres Foot": "soccer"
    },
    "🏀 BASKET": {
        "🇺🇸 NBA": "basketball_nba", "🇪🇺 Euroligue": "basketball_euroleague",
        "🇫🇷 France LNB": "basketball_france_lnb", "🌍 Autres Basket": "basketball"
    },
    "HOCKEY / BASEBALL": {
        "🏒 NHL": "icehockey_nhl", "⚾ MLB": "baseball_mlb",
        "🏒 KHL": "icehockey_khl", "⚾ Corée KBO": "baseball_kbo"
    }
}

# --- ANALYSE AVANCÉE (SCORE & POINTS) ---
def generer_analyse_complete(m_h, m_a, sport, h_n, a_n, date_match):
    p_v1, p_v2, p_n = 0, 0, 0
    # Calcul Probabilités
    if "basketball" not in sport:
        for i in range(10):
            for j in range(10):
                prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
                if i > j: p_v1 += prob
                elif i < j: p_v2 += prob
                else: p_n += prob
    else:
        p_v1 = (m_h**14) / (m_h**14 + m_a**14) if (m_h+m_a) > 0 else 0.5
        p_v2 = 1 - p_v1
        p_n = 0.02

    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    fav_name = h_n if v1 > v2 else a_n
    fav_avg = m_h if v1 > v2 else m_a
    total_match = round(m_h + m_a, 2)
    
    # Label selon le sport
    label = "Buts" if "soccer" in sport or "icehockey" in sport else "Points"
    if "baseball" in sport: label = "Runs"

    dt_obj = datetime.fromisoformat(date_match.replace('Z', '+00:00'))
    heure_fiat = dt_obj.strftime("%d/%m %H:%M")

    msg = (f"🏟 **{h_n} vs {a_n}**\n"
           f"⏰ {heure_fiat} GMT\n\n"
           f"📊 **PROBABILITÉS :**\n"
           f"🏠 {h_n}: {round(v1,1)}% | 🤝 Nul: {round(n,1)}% | 🚀 {a_n}: {round(v2,1)}%\n\n"
           f"🎯 **ESTIMATIONS SCORES :**\n"
           f"▪️ Total Match : **{total_match}** {label}\n"
           f"▪️ {fav_name} : **{round(fav_avg, 2)}** {label}\n\n"
           f"💎 **CONSEIL :**\n"
           f"👉 Plus de {round(total_match * 0.8, 1)} {label} dans le match\n"
           f"👉 {fav_name} marque + de {round(fav_avg * 0.7, 1)} {label}")
    
    return msg, [v1, n, v2, v1+n, v2+n], round(max(v1, v2), 1)

# --- SCANNER ---
def executer_scan(sport_key, limit_hours=24, is_selection=False):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        maintenant = datetime.utcnow()
        limite = maintenant + timedelta(hours=limit_hours)
        matchs_trouves = []

        for m in events:
            date_m = datetime.fromisoformat(m['commence_time'].replace('Z', '+00:00')).replace(tzinfo=None)
            if maintenant <= date_m <= limite:
                h, a = m['home_team'], m['away_team']
                try:
                    odds = m['bookmakers'][0]['markets'][0]['outcomes']
                    c_h = next(o['price'] for o in odds if o['name'] == h)
                    c_a = next(o['price'] for o in odds if o['name'] == a)
                    
                    # Ajustement des moyennes selon le sport (Power Ratings)
                    if "soccer" in sport_key: m_h, m_a = 1.5/c_h*2.6, 1.1/c_a*2.6
                    elif "basketball" in sport_key: m_h, m_a = 115/c_h, 110/c_a
                    elif "icehockey" in sport_key: m_h, m_a = 3.2/c_h*2.2, 2.8/c_a*2.2
                    else: m_h, m_a = 5.0/c_h, 4.5/c_a # Baseball

                    text, vals, conf = generer_analyse_complete(m_h, m_a, sport_key, h, a, m['commence_time'])
                    matchs_trouves.append({'text': text, 'vals': vals, 'conf': conf})
                except: continue
        
        return sorted(matchs_trouves, key=lambda x: x['conf'], reverse=True)[:(1 if is_selection else 5)]
    except: return []

# --- INTERFACE TELEGRAM ---
@bot.message_handler(commands=['start', 'menu'])
def menu_principal(message):
    markup = InlineKeyboardMarkup(row_width=1)
    for s in SPORTS_DATA.keys():
        markup.add(InlineKeyboardButton(s, callback_data=f"cat_{s}"))
    markup.add(InlineKeyboardButton("⭐ SÉLECTION SÛRE (Multi)", callback_data="selection_top"))
    bot.send_message(message.chat.id, "📊 **PREDICTPRO V20**\nDonnées statistiques & Scores estimés :", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("cat_"):
        cat = call.data.replace("cat_", "")
        markup = InlineKeyboardMarkup(row_width=2)
        for nom, key in SPORTS_DATA[cat].items():
            markup.add(InlineKeyboardButton(nom, callback_data=f"run_{key}"))
        markup.add(InlineKeyboardButton("⬅️ Retour", callback_data="back"))
        bot.edit_message_text(f"🏆 {cat}\nChoisissez votre ligue :", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("run_"):
        key = call.data.replace("run_", "")
        bot.answer_callback_query(call.id, "Calcul des probabilités...")
        res = executer_scan(key)
        envoyer_resultats(call.message.chat.id, res)

    elif call.data == "selection_top":
        bot.answer_callback_query(call.id, "Analyse des meilleures cotes...")
        picks = []
        for s in ["soccer_epl", "basketball_nba", "icehockey_nhl"]:
            picks.extend(executer_scan(s, 24, True))
        envoyer_resultats(call.message.chat.id, picks)

    elif call.data == "back": menu_principal(call.message)

def envoyer_resultats(chat_id, matchs):
    if not matchs:
        bot.send_message(chat_id, "📭 Aucun match disponible.")
        return
    for m in matchs:
        plt.figure(figsize=(5,3))
        plt.bar(['V1', 'N', 'V2', '1N', 'N2'], m['vals'], color=['#3498db','#95a5a6','#e74c3c','#2ecc71','#27ae60'])
        plt.title("Probabilités de Résultat (%)")
        path = f"p_{int(time.time())}.png"
        plt.savefig(path); plt.close()
        with open(path, "rb") as f:
            bot.send_photo(chat_id, f, caption=m['text'], parse_mode='Markdown')
        os.remove(path)
        time.sleep(1)

# --- SERVER ---
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.infinity_polling()
