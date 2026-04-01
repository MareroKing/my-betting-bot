import telebot, requests, time, os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
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
def home(): return "PredictPro V20 est en ligne !"

bot = telebot.TeleBot(TOKEN)

# --- STRUCTURE DES LIGUES ---
SPORTS_DATA = {
    "⚽ FOOTBALL": {
        "🇫🇷 Ligue 1": "soccer_france_ligue_one",
        "🇪🇸 La Liga": "soccer_spain_la_liga",
        "🇬🇧 Premier League": "soccer_epl",
        "🇮🇹 Serie A": "soccer_italy_serie_a",
        "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
        "🇳🇱 Eredivisie": "soccer_netherlands_eredivisie",
        "🇧🇪 Jupiler Pro": "soccer_belgium_jupiler_league",
        "🇵🇹 Portugal D1": "soccer_portugal_primeira_liga",
        "🇹🇷 Turquie D1": "soccer_turkey_super_league",
        "🌍 Autres Foot": "soccer"
    },
    "🏀 BASKET": {
        "🇺🇸 NBA": "basketball_nba",
        "🎓 NCAA": "basketball_ncaa",
        "🇫🇷 France LNB": "basketball_france_lnb",
        "🇪🇸 Espagne ACB": "basketball_spain_liga_acb",
        "🇪🇺 Euroligue": "basketball_euroleague",
        "🌍 Autres Basket": "basketball"
    },
    "🏒 HOCKEY": {
        "🇺🇸 NHL": "icehockey_nhl",
        "🇷🇺 KHL": "icehockey_khl",
        "🇸🇪 Suède": "icehockey_sweden_allsvenskan",
        "🇨🇭 Suisse": "icehockey_switzerland_nla",
        "🌍 Autres Hockey": "icehockey"
    },
    "⚾ BASEBALL": {
        "🇺🇸 MLB": "baseball_mlb",
        "🇰🇷 Corée du Sud": "baseball_kbo",
        "🇯🇵 Japon NPB": "baseball_njp",
        "🌍 Autres": "baseball"
    }
}

# --- LOGIQUE D'ANALYSE STATISTIQUE ---
def generer_analyse(m_h, m_a, sport, h_n, a_n, date_match):
    p_v1, p_v2, p_n = 0, 0, 0
    if "basketball" not in sport:
        for i in range(12):
            for j in range(12):
                prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
                if i > j: p_v1 += prob
                elif i < j: p_v2 += prob
                else: p_n += prob
    else:
        p_v1 = (m_h**14) / (m_h**14 + m_a**14) if (m_h+m_a) > 0 else 0.5
        p_v2 = 1 - p_v1
        p_n = 0.02

    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    gagnant = h_n if v1 > v2 else a_n
    confiance = round(max(v1, v2), 1)
    
    dt_obj = datetime.fromisoformat(date_match.replace('Z', '+00:00'))
    heure_fiat = dt_obj.strftime("%d/%m %H:%M")

    msg = (f"🏟 **{h_n} vs {a_n}**\n"
           f"⏰ {heure_fiat} GMT\n\n"
           f"📊 **Probabilités :**\n"
           f"  • {h_n} : {round(v1,1)}%\n"
           f"  • Nul : {round(n,1)}%\n"
           f"  • {a_n} : {round(v2,1)}%\n\n"
           f"💎 **PRÉDICTION :** {gagnant}\n"
           f"🛡 **SÉCURITÉ :** Double Chance ({round(max(v1+n, v2+n),1)}%)")
    
    return msg, [v1, n, v2, v1+n, v2+n], confiance

# --- SCANNER DE MATCHS ---
def scanner_ligue(sport_key, limit_hours=24, is_selection=False):
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
                    
                    if "soccer" in sport_key: m_h, m_a = 1.6/c_h*2.6, 1.2/c_a*2.6
                    elif "basketball" in sport_key: m_h, m_a = 112/c_h, 108/c_a
                    else: m_h, m_a = 3.2/c_h*2, 2.8/c_a*2

                    text, vals, conf = generer_analyse(m_h, m_a, sport_key, h, a, m['commence_time'])
                    matchs_trouves.append({'text': text, 'vals': vals, 'conf': conf, 'teams': f"{h}-{a}"})
                except: continue

        if is_selection:
            return sorted(matchs_trouves, key=lambda x: x['conf'], reverse=True)[:1]
        return matchs_trouves[:5]
    except:
        return []

# --- GESTIONNAIRE TELEGRAM ---
@bot.message_handler(commands=['start', 'menu'])
def show_menu(message):
    markup = InlineKeyboardMarkup(row_width=2)
    btns = [InlineKeyboardButton(s, callback_data=f"m_{s}") for s in SPORTS_DATA.keys()]
    markup.add(*btns)
    markup.add(InlineKeyboardButton("🔥 SÉLECTION DU JOUR 🔥", callback_data="selection"))
    bot.send_message(message.chat.id, "🤖 **PREDICTPRO V20**\nChoisissez une discipline :", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith("m_"):
        sport_name = call.data.replace("m_", "")
        markup = InlineKeyboardMarkup(row_width=2)
        for label, key in SPORTS_DATA[sport_name].items():
            markup.add(InlineKeyboardButton(label, callback_data=f"s_{key}"))
        markup.add(InlineKeyboardButton("⬅️ Retour", callback_data="back"))
        bot.edit_message_text(f"📍 **{sport_name}**\nSélectionnez la ligue :", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

    elif call.data.startswith("s_"):
        key = call.data.replace("s_", "")
        bot.answer_callback_query(call.id, "Analyse en cours...")
        matchs = scanner_ligue(key)
        envoyer_resultats(call.message.chat.id, matchs)

    elif call.data == "selection":
        bot.answer_callback_query(call.id, "Recherche des meilleures pépites...")
        bot.send_message(call.message.chat.id, "💎 **TOP 3 SÉLECTION MULTI-SPORT**")
        pépites = []
        for sport in ["soccer_epl", "basketball_nba", "icehockey_nhl"]:
            pépites.extend(scanner_ligue(sport, 24, True))
        envoyer_resultats(call.message.chat.id, pépites)

    elif call.data == "back":
        show_menu(call.message)

def envoyer_resultats(chat_id, matchs):
    if not matchs:
        bot.send_message(chat_id, "📭 Aucun match imminent trouvé.")
        return
    for m in matchs:
        plt.figure(figsize=(5,3))
        plt.bar(['V1', 'N', 'V2', '1N', 'N2'], m['vals'], color=['#3498db','#95a5a6','#e74c3c','#2ecc71','#27ae60'])
        plt.ylim(0, 100)
        path = f"p_{int(time.time())}.png"
        plt.savefig(path); plt.close()
        with open(path, "rb") as f:
            bot.send_photo(chat_id, f, caption=m['text'], parse_mode='Markdown')
        os.remove(path)
        time.sleep(1)

# --- RUN ---
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    print("Bot PredictPro démarré !")
    bot.infinity_polling()
