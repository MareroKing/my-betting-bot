import telebot, requests, time, os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from scipy.stats import poisson
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION DES VARIABLES ---
# Il est fortement conseillé de les configurer dans le Dashboard Render (Environment Variables)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8695595150:AAFBws8bBEwnRXe_ooZ2zY1jKxt9jhwMQww")
CHAT_ID = os.getenv("CHAT_ID", "1206877909")
API_KEY_ODDS = os.getenv("ODDS_API_KEY", "3d26e46535751ecf611f0a42f083f33a")

app = Flask('')

@app.route('/')
def home():
    return "PredictPro V20 est en ligne et opérationnel !"

bot = telebot.TeleBot(TOKEN)

# --- STRUCTURE DES MENUS ---
SPORTS_DATA = {
    "⚽ FOOTBALL": {
        "🇫🇷 Ligue 1": "soccer_france_ligue_one",
        "🇪🇸 La Liga": "soccer_spain_la_liga",
        "🇬🇧 Premier League": "soccer_epl",
        "🇮🇹 Serie A": "soccer_italy_serie_a",
        "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
        "🇳🇱 Eredivisie": "soccer_netherlands_eredivisie",
        "🇵🇹 Portugal D1": "soccer_portugal_primeira_liga",
        "🇧🇪 Jupiler Pro": "soccer_belgium_jupiler_league",
        "🇹🇷 Turquie D1": "soccer_turkey_super_league",
        "🌍 Autres Foot": "soccer"
    },
    "🏀 BASKETBALL": {
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
        "🇰🇷 Corée KBO": "baseball_kbo",
        "🇯🇵 Japon NPB": "baseball_njp",
        "🌍 Autres Baseball": "baseball"
    }
}

# --- LOGIQUE D'ANALYSE ---
def generer_analyse_v20(m_h, m_a, sport, h_n, a_n, date_match):
    p_v1, p_v2, p_n = 0, 0, 0
    
    if "basketball" not in sport:
        for i in range(12):
            for j in range(12):
                prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a)
                if i > j: p_v1 += prob
                elif i < j: p_v2 += prob
                else: p_n += prob
    else:
        p_v1 = (m_h**13.5) / (m_h**13.5 + m_a**13.5) if (m_h+m_a) > 0 else 0.5
        p_v2 = 1 - p_v1
        p_n = 0.02

    v1, v2, n = p_v1*100, p_v2*100, p_n*100
    fav_team = h_n if v1 > v2 else a_n
    fav_exp = m_h if v1 > v2 else m_a
    total_estime = round(m_h + m_a, 2)
    
    if "soccer" in sport or "icehockey" in sport: unit = "Buts"
    elif "basketball" in sport: unit = "Points"
    else: unit = "Runs"

    dt_obj = datetime.fromisoformat(date_match.replace('Z', '+00:00'))
    heure_fiat = dt_obj.strftime("%d/%m %H:%M")

    msg = (f"🏟 **{h_n} vs {a_n}**\n"
           f"⏰ {heure_fiat} GMT\n\n"
           f"📊 **PROBABILITÉS :**\n"
           f"🏠 {h_n}: {round(v1,1)}% | 🤝 Nul: {round(n,1)}% | 🚀 {a_n}: {round(v2,1)}%\n\n"
           f"🎯 **ESTIMATIONS SCORES :**\n"
           f"▪️ Total Match : **{total_estime}** {unit}\n"
           f"▪️ {fav_team} : **{round(fav_exp, 2)}** {unit}\n\n"
           f"💎 **CONSEIL :**\n"
           f"👉 Plus de {round(total_estime * 0.75, 1)} {unit} au total\n"
           f"👉 {fav_team} marque + de {round(fav_exp * 0.7, 1)} {unit}")
    
    return msg, [v1, n, v2, v1+n, v2+n], round(max(v1, v2), 1)

# --- FONCTION DE SCAN ---
def lancer_scan(sport_key, is_selection=False):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h"
        events = requests.get(url).json()
        maintenant = datetime.utcnow()
        limite = maintenant + timedelta(hours=24)
        matchs_trouves = []

        for m in events:
            date_m = datetime.fromisoformat(m['commence_time'].replace('Z', '+00:00')).replace(tzinfo=None)
            if maintenant <= date_m <= limite:
                h, a = m['home_team'], m['away_team']
                try:
                    odds = m['bookmakers'][0]['markets'][0]['outcomes']
                    c_h = next(o['price'] for o in odds if o['name'] == h)
                    c_a = next(o['price'] for o in odds if o['name'] == a)
                    
                    if "soccer" in sport_key: m_h, m_a = 1.4/c_h*2.6, 1.0/c_a*2.6
                    elif "basketball" in sport_key: m_h, m_a = 114/c_h, 109/c_a
                    elif "icehockey" in sport_key: m_h, m_a = 3.3/c_h*2.1, 2.9/c_a*2.1
                    else: m_h, m_a = 4.8/c_h, 4.2/c_a # Baseball

                    text, vals, conf = generer_analyse_v20(m_h, m_a, sport_key, h, a, m['commence_time'])
                    matchs_trouves.append({'text': text, 'vals': vals, 'conf': conf})
                except: continue
        
        if is_selection:
            return sorted(matchs_trouves, key=lambda x: x['conf'], reverse=True)[:1]
        return matchs_trouves[:5]
    except: return []

# --- HANDLERS TELEGRAM ---
@bot.message_handler(commands=['start', 'menu'])
def menu_principal(message):
    markup = InlineKeyboardMarkup(row_width=1)
    for sport in SPORTS_DATA.keys():
        markup.add(InlineKeyboardButton(sport, callback_data=f"cat_{sport}"))
    markup.add(InlineKeyboardButton("⭐ SÉLECTION DU JOUR (Top 3)", callback_data="top_selection"))
    bot.send_message(message.chat.id, "💎 **PREDICTPRO V20**\nChoisissez une discipline :", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    if call.data.startswith("cat_"):
        cat = call.data.replace("cat_", "")
        markup = InlineKeyboardMarkup(row_width=2)
        for nom, key in SPORTS_DATA[cat].items():
            markup.add(InlineKeyboardButton(nom, callback_data=f"run_{key}"))
        markup.add(InlineKeyboardButton("⬅️ Retour", callback_data="back"))
        bot.edit_message_text(f"🏆 {cat}\nChoisissez la ligue ou 'Autres' :", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("run_"):
        key = call.data.replace("run_", "")
        bot.answer_callback_query(call.id, "Analyse en cours...")
        res = lancer_scan(key)
        envoyer_photos(call.message.chat.id, res)

    elif call.data == "top_selection":
        bot.answer_callback_query(call.id, "Calcul des probabilités...")
        bot.send_message(call.message.chat.id, "🔥 **SÉLECTION DU JOUR**")
        picks = []
        for s in ["soccer_epl", "basketball_nba", "icehockey_nhl"]:
            picks.extend(lancer_scan(s, is_selection=True))
        envoyer_photos(call.message.chat.id, picks)

    elif call.data == "back":
        menu_principal(call.message)

def envoyer_photos(chat_id, matchs):
    if not matchs:
        bot.send_message(chat_id, "📭 Aucun match trouvé pour les prochaines 24h.")
        return
    for m in matchs:
        plt.figure(figsize=(5,3))
        plt.bar(['V1', 'N', 'V2', '1N', 'N2'], m['vals'], color=['#3498db','#95a5a6','#e74c3c','#2ecc71','#27ae60'])
        plt.ylim(0, 100)
        plt.title("Probabilités de Résultat")
        path = f"p_{int(time.time())}.png"
        plt.savefig(path); plt.close()
        with open(path, "rb") as f:
            bot.send_photo(chat_id, f, caption=m['text'], parse_mode='Markdown')
        if os.path.exists(path):
            os.remove(path)
        time.sleep(1)

# --- LANCEMENT ---
def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    # Thread Flask pour Render
    Thread(target=run_flask).start()
    
    # Suppression du webhook pour éviter l'erreur 409
    bot.remove_webhook()
    time.sleep(1)
    
    print("Bot PredictPro opérationnel !")
    # Infinity polling avec timeout pour la stabilité
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
