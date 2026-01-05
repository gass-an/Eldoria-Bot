# Utiliser une image de base Python 3
FROM python:3.11-slim


# Définir le répertoire de travail dans le conteneur
WORKDIR /app


# Copier tous les fichiers du projet dans le conteneur
COPY . /app


# Installer les dépendances
RUN pip install -r requirements.txt


# Spécifier la commande de démarrage pour exécuter main.py
CMD ["python", "src/main.py"]

