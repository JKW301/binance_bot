import threading
import time
import sys
from trading_live import run_live_trading, initialize_binance  # Import du script de trading

# Signal global pour arrêter/redémarrer
stop_event = threading.Event()

def monitor_input():
    """
    Écoute les entrées utilisateur pour gérer les commandes.
    Appuyez sur 'q' pour quitter ou 'r' pour relancer le script.
    """
    global stop_event
    while True:
        user_input = input("Appuyez sur 'q' pour quitter ou 'r' pour relancer : ").strip().lower()
        if user_input == 'q':
            print("[INFO] Arrêt demandé par l'utilisateur.")
            stop_event.set()  # Signal d'arrêt
            break
        elif user_input == 'r':
            print("[INFO] Redémarrage du script...")
            stop_event.set()  # Arrêter l'exécution actuelle
            stop_event.clear()  # Réinitialiser le signal d'arrêt
            threading.Thread(target=start_trading, daemon=True).start()  # Relancer

def start_trading():
    """
    Fonction pour lancer ou relancer le trading.
    """
    try:
        print("[INFO] Initialisation du trading...")
        run_live_trading()  # Appelle la fonction de trading principale
    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'exécution du trading : {e}")

if __name__ == "__main__":
    print("[INFO] Lancement du programme.")
    # Démarrage initial du trading dans un thread séparé
    threading.Thread(target=start_trading, daemon=True).start()

    # Écoute les commandes utilisateur dans le thread principal
    monitor_input()

    print("[INFO] Programme terminé.")
