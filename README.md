
<<<<<<< HEAD
# binance_bot

Pour construire l'image Docker :

```bash
sudo docker build -t binance-bot .
```

Pour exécuter le conteneur Docker :

```bash
sudo docker run --env-file .env binance-bot
```
=======
# 🚀 Binance Futures Trading Bot
> **Note** : Ce bot est à usage éducatif. Utilisez-le avec précaution et testez toutes vos stratégies avant de les appliquer avec des fonds réels.
Un bot de trading automatisé conçu pour interagir avec l'API Binance Futures.  
Il utilise des stratégies comme Ichimoku pour analyser les marchés et placer des ordres tout en gérant les risques à l'aide de stop-loss dynamiques.  

---

## 🌟 Fonctionnalités Principales

- **Connexion Automatique** : Initialisation sécurisée avec les clés API stockées dans un fichier `.env`.  
- **Stratégie Intégrée** : Analyse Ichimoku pour détecter des signaux de trading robustes.  
- **Gestion des Risques** : Calcul automatique du stop-loss basé sur le capital et le risque défini.  
- **Compatibilité Binance Futures** : Testé sur le Testnet Binance Futures pour éviter tout risque en environnement réel.  
- **Journalisation des Transactions** : Enregistrement des ordres dans un fichier CSV pour suivi et analyse.

---

## 🛠️ Installation et Configuration

### Prérequis

- **Python 3.8+**
- Bibliothèques nécessaires :
  - `python-binance`
  - `python-dotenv`
  - `pandas`
  - `colorama`

Installez les dépendances avec :
```bash
pip install -r requirements.txt
```

### Configuration

1. **Clés API Binance** :
   - Créez un fichier `.env` à la racine du projet et ajoutez vos clés API :
     ```plaintext
     API_KEY=VOTRE_CLE_API
     API_SECRET=VOTRE_CLE_SECRETE
     ```

2. **Mode Testnet** :
   Assurez-vous que votre compte Binance est configuré pour utiliser le Testnet pour éviter tout risque financier.

3. **Paramètres Personnalisables** :
   - Modifiez `MAX_POSITIONS` et `CSV_FILE` dans `trading_live.py` selon vos besoins.

---

## 🚀 Utilisation

1. **Lancez le Bot** :
   Exécutez simplement :
   ```bash
   python trading_live.py
   ```

2. **Suivi en Direct** :
   - Le bot affichera en temps réel :
     - Les positions ouvertes.
     - Les signaux détectés.
     - Les ordres placés et les erreurs éventuelles.

3. **Journalisation** :
   Toutes les transactions sont enregistrées dans un fichier CSV nommé `trading_operations.csv`.

---

## 🧩 Structure du Projet

```plaintext
.
├── trading_live.py          # Script principal du bot
├── strategy_ichimoku.py     # Stratégies de trading (ex : Ichimoku)
├── stop_loss_related.py     # Gestion des stop-loss
├── positions.py             # Fonctions pour récupérer les positions
├── ux_interface.py          # Interface utilisateur et journalisation
├── ux_load_idle.py          # Animation et progression
├── timeframes.py            # Gestion des intervalles de temps
├── .env                     # Clés API (non versionné)
├── requirements.txt         # Liste des dépendances Python
├── LICENSE                  # Licence du projet
└── README.md                # Documentation
```

---

## ⚙️ Fonctionnalités Techniques

### Calcul des Stop-Loss
Le bot utilise une méthode robuste pour calculer les stop-loss dynamiques :
- Basé sur le capital total.
- Ajusté au **tickSize** et aux contraintes de Binance.

### Stratégie Ichimoku
La stratégie Ichimoku analyse les données des chandeliers pour détecter les signaux de tendance et de renversement.

### Gestion des Positions
- Limite du nombre de positions ouvertes via `MAX_POSITIONS`.
- Journalisation des positions dans un fichier CSV.

---

## 🛡️ Sécurité

- **Clés API** : Assurez-vous que vos clés API ont des permissions limitées (pas de retrait de fonds).  
- **Testnet** : Utilisez toujours le Testnet pour tester vos stratégies avant de trader en production.  
- **Risques Financiers** : Ce bot est fourni "tel quel" et l'auteur ne peut être tenu responsable des pertes éventuelles.

---

## 📜 Licence

Ce projet est sous licence.

---

## 🛠️ Contribution

Les contributions sont les bienvenues ! Si vous souhaitez proposer des améliorations ou signaler des bugs, ouvrez une issue ou un pull request dans ce dépôt.

---
>>>>>>> origin/main
