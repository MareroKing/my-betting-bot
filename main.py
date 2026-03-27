import telebot
import requests
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION DU SERVEUR (POUR RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "PredictPro Bot is Live and Stable!"

def run():
    # Render utilise le port 10000 par défaut pour les Web Services
    app.run(host='0.0.0.0', port=10000)

# --- 2. VOS PARAMÈTRES ---
TOKEN = "8695595150:AAGPxvoX4bOFaKgnu9bdyzE6Nqy2Mi4pGt4"
CHAT_ID = "1206877909"
API_KEY_ODDS = "119631c89710538cd7d975da53782987" 

bot = telebot.TeleBot(TOKEN)

# --- 3. LOGIQUE MATHÉMATIQUE (Loi de Poisson) ---
def calculer_proba_poisson(m_dom, m_ext):
    p_gagne = 0
    for i in range(1, 6): 
        for j in range(0, i): 
            p_gagne += poisson.pmf(i, m_dom) * poisson.pmf(j, m_ext)
    return round(p_gagne * 100, 1)

# --- 4. ENVOI DES ALERTES GRAPHIQUES ---
def generer_et_envoyer(h, a, p_bot, p_book, cote, sport):
    try:
        plt.figure(figsize=(7,4))
        plt.bar(['PredictPro', 'Bookmaker'], [p_bot, p_book], color=['#27ae60', '#7f8c8d'])
        plt.axhline(y=p_book, color='red', linestyle='--', alpha=0.5)
        plt.title(f"Analyse Value : {h}")
        plt.ylabel("Probabilité (%)")
        plt.ylim(0, 100)
        
        plt.savefig("analyse.png")
        plt.close()
        
        msg = (f"🎯 **ALERTE VALUE DÉTECTÉE**\n\n"
               f"🏟 **Match :** {h} vs {a}\n"
               f"🏆 **Ligue :** {sport}\n"
               f"📈 **Cote :** {cote}\n"
               f"🔥 **Confiance Bot :** {p_bot}%\n"
               f"📊 **Confiance Marché :** {p_book:.1f}%")
        
        with open("analyse.png", "rb") as img:
            bot.send_photo(CHAT_ID, img, caption=msg, parse_mode='Markdown')
    except Exception as e:
        print(f"Erreur envoi graphique : {e}")

# --- 5. MOTEUR DE SCAN ---
def lancer_scan():
    print("🚀 Scan Multi-Marchés en cours...")
    sports = ["soccer_france_ligue_1", "soccer_spain_la_liga", "soccer_germany_bundesliga", "icehockey_nhl", "baseball_mlb"]
    matchs_analyses = 0
    opportunites_trouvees = 0
    
    for s in sports:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{s}/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=h2h,totals"
            events = requests.get(url).json()
            
            if isinstance(events, list):
                for m in events[:8]: # On analyse un peu plus de matchs
                    matchs_analyses += 1
                    h, a = m['home_team'], m['away_team']
                    stats = probas_completes(2.1, 1.2) # On va dynamiser ça après
                    
                    # Logique de détection (Victoire, Over, etc.)
                    # ... (garde ton code de détection ici) ...
                    # Si une alerte est envoyée : opportunites_trouvees += 1

        except Exception as e: print(f"Erreur {s}: {e}")
    
    # RAPPORT FINAL
    rapport = f"📊 **Rapport de Scan**\n✅ Matchs analysés : {matchs_analyses}\n🔥 Opportunités trouvées : {opportunites_trouvees}"
    bot.send_message(CHAT_ID, rapport, parse_mode='Markdown')
    print(f"✅ Fin du scan. {matchs_analyses} matchs vus.")

# --- 6. COMMANDES INTERACTIVES ---
@bot.message_handler(commands=['start', 'aide'])
def send_welcome(message):
    help_text = (
        "🤖 **Assistant PredictPro**\n\n"
        "Je surveille les cotes pour toi.\n"
        "👉 `/scan` : Lance une analyse manuelle immédiate.\n"
        "👉 `/aide` : Affiche ce menu."
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['scan'])
def manual_scan(message):
    bot.reply_to(message, "🔎 Scan manuel demandé... Analyse en cours.")
    lancer_scan()
    bot.send_message(CHAT_ID, "✅ Scan manuel terminé.")

# --- 7. MULTI-THREADING ET ÉVITEMENT DE CONFLIT ---
def boucle_automatique():
    # Attente initiale pour laisser le polling démarrer proprement
    time.sleep(10)
    while True:
        lancer_scan()
        time.sleep(3600)

if __name__ == "__main__":
    # 1. Lancement des ouvriers en arrière-plan
    Thread(target=run, daemon=True).start()
    Thread(target=boucle_automatique, daemon=True).start()

    print("🤖 Bot PredictPro : Tentative de connexion propre...")

    # 2. BOUCLE DE SURVIE ANTI-CONFLIT
    while True:
        try:
            print("🔄 Nettoyage des sessions précédentes...")
            bot.remove_webhook()
            time.sleep(2)
            
            print("🚀 Lancement du Polling...")
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=5)
            
        except Exception as e:
            if "Conflict" in str(e):
                print("⚠️ Conflit détecté (doublon). Nouvelle tentative dans 5 secondes...")
                time.sleep(5)
            else:
                print(f"❌ Erreur imprévue : {e}")
                time.sleep(10)
