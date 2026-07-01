# Utiliser une image Python légère basée sur Debian Slim
FROM python:3.11-slim

# Empêcher Python de générer les fichiers .pyc (__pycache__)
ENV PYTHONDONTWRITEBYTECODE=1

# Définir le répertoire de travail du conteneur
WORKDIR /app

# Installer les données de fuseaux horaires (utilisées par zoneinfo)
# puis nettoyer le cache APT pour réduire la taille de l'image
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non privilégié pour exécuter l'application
# afin de limiter les risques en cas de compromission
RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app appuser

# Copier le fichier des dépendances séparément pour optimiserle cache Docker :
# les dépendances ne sont réinstallées que sirequirements.txt est modifié
COPY requirements.txt .

# Mettre à jour pip puis installer les dépendances sans conserver
# le cache afin de réduire la taille de l'image
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copier le code source de l'application
COPY resources ./resources
COPY assets ./assets
COPY src ./src

# Donner les droits de lecture/écriture sur l'application à l'utilisateur non privilégié
RUN chown -R appuser:appuser /app

# Exécuter l'application avec l'utilisateur non-root
USER appuser

# Lancer le bot
CMD ["python", "src/main.py"]