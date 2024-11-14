import math
import time
import sys
import pandas as pd
from binance.client import Client
from binance.enums import *
#from combined_BTC import ichimoku, is_bullish_convergence, is_bearish_convergence
import csv
from colorama import Fore, Style, init
init(autoreset=True)

def loading_spinner(duration):
    """Affiche un spinner animé pendant une durée spécifiée."""
    spinner = ['|', '/', '-', '\\']
    end_time = time.time() + duration
    idx = 0

    while time.time() < end_time:
        sys.stdout.write(f"\r{spinner[idx % len(spinner)]} Chargement en cours...")
        sys.stdout.flush()
        time.sleep(0.1)
        idx += 1
    
    sys.stdout.write("\r✔ Chargement terminé!         \n")

def progress_bar_with_sleep(duration, stop_event=None):
    """Affiche une barre de progression pendant une durée spécifiée, avec gestion d'un signal d'arrêt."""
    total_steps = 60  # Nombre de segments dans la barre
    interval = duration / total_steps  # Intervalle de mise à jour

    for step in range(total_steps + 1):
        if stop_event and stop_event.is_set():  # Arrêt propre si signal activé
            sys.stdout.write("\r[ INTERRUPTION ] Arrêt demandé. Nettoyage...\n")
            sys.stdout.flush()
            break
        
        percent = (step / total_steps) * 100
        bar = '=' * step + '-' * (total_steps - step)
        sys.stdout.write(f"\r[ {bar} ] {percent:.2f}%")
        sys.stdout.flush()
        time.sleep(interval)
    
    else:  # Si la boucle n'est pas interrompue
        sys.stdout.write("\n✔ Progression terminée!\n")


def log_operation_to_csv(file_name, operation_data):
    """Enregistre les données d'une opération dans un fichier CSV."""
    file_exists = os.path.isfile(file_name)
    with open(file_name, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=operation_data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(operation_data)