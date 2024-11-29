# Utiliser une image Python officielle
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers du projet dans le conteneur
COPY . .

# Installer les bibliothèques nécessaires
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir python-dotenv pandas python-binance colorama matplotlib requests

# Exposer un port, si nécessaire
EXPOSE 5000

# Charger les variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV $(cat .env | xargs)

# Définir la commande par défaut pour exécuter le script principal
CMD ["python", "main.py"]
