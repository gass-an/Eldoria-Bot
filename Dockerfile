# Utiliser une image de base Python 3
FROM python:3.11-slim

# Installer tzdata pour le support des fuseaux horaires (zoneinfo)
# et nettoyer le cache APT pour réduire la taille de l’image finale
RUN apt-get update \
    && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*


# Définir le répertoire de travail dans le conteneur
WORKDIR /app


# Copier tous les fichiers du projet dans le conteneur
COPY . /app


# Installer les dépendances
RUN pip install -r requirements.txt


# Spécifier la commande de démarrage pour exécuter main.py
CMD ["python", "src/main.py"]

