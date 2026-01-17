# 🧙 Eldoria — Bot Discord

![Python](https://img.shields.io/static/v1?label=Python&message=3.11%2B&color=blueviolet&logo=python)
![py-cord](https://img.shields.io/static/v1?label=py-cord&message=2.7.0%2B&color=blueviolet&logo=python&logoColor=white)
![Discord](https://img.shields.io/static/v1?label=Discord&message=Bot&color=5865F2&logo=discord&logoColor=white)
![Docker](https://img.shields.io/static/v1?label=Docker&message=Ready&color=0db7ed&logo=docker&logoColor=white)  
![Status](https://img.shields.io/badge/⚙️%20Status-En%20développement-yellow)
![Version](https://img.shields.io/github/v/tag/gass-an/Eldoria-Bot?label=Version&color=darkgreen&sort=semver&logo=github&logoColor=white)


> **Eldoria** est un bot Discord développé en Python avec **py-cord**, conçu pour enrichir ton serveur avec des commandes interactives et des fonctionnalités personnalisées.



## ✨ Fonctionnalités

### ⚙️ Côté technique

- 🤖 Bot Discord basé sur **py-cord**
- ⚙️ Configuration via fichier `.env`
- 🐳 Lancement simple avec **Docker**
- 📦 Architecture modulaire prête pour ajouter des extensions (cogs)

### 🪄 Commandes & systèmes du bot

Eldoria propose plusieurs familles de commandes slash pour gérer et animer ton serveur :

- **📈 Système d’XP & niveaux** :  
Gain d’XP automatique, classement, rôles par niveau et configuration complète par les admins.

- **😀 Reaction Roles** :  
Attribution automatique de rôles via réactions sur des messages spécifiques.

- **🕵️ Secret Roles** :  
Attribution de rôles lorsqu’un utilisateur envoie un message secret dans un salon défini.

- **🔊 Salons vocaux temporaires** :  
Création automatique de salons vocaux lorsqu’un utilisateur rejoint un salon “parent”.

- **💾 Sauvegarde & restauration de la base de données** :  
Sauvegarde manuelle de la base SQLite dans un salon dédié et restauration via fichier.

- **🧭 Commandes de base** :  
/help pour lister les commandes et /ping pour vérifier l’état du bot.

- **👋 Message d’arrivée** :  
Envoi automatique d’un message d’accueil aléatoire lors de l’arrivée d’un nouvel utilisateur.


## 🧱 Prérequis

- Python **3.11+**
- Un bot Discord et son **TOKEN**
- (Optionnel) Docker



## 🚀 Lancer avec Docker Compose (recommandé)

### Prérequis
- Docker
- Docker Compose (plugin `docker compose`)

### 1. Configurer l'environnement
Crée un fichier **`.env`** à la racine du projet.  
Suivre le `.env .exemple` comme exemple.

### 2. Démarrer le bot
```bash
docker compose up --build -d
```

### 3. Voir les logs
```bash
docker compose logs -f
```

### 4. Arrêter le bot
```bash
docker compose down
```

### 📦 Données persistées
Le `docker-compose.yml` monte les volumes suivants :
- `./data -> /app/data` : base de données SQLite et fichiers générés
- `./json -> /app/json` (lecture seule) : fichiers de configuration

Pour réinitialiser complètement :
```bash
docker compose down -v
rm -rf data
```

## 🚀 Installation (sans Docker)

### 1. Cloner le projet

```bash
git clone https://github.com/gass-an/eldoria.git
cd eldoria
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer l’environnement
Crée un fichier **`.env`** à la racine du projet.  
Suivre le `.env .exemple` comme exemple.

### 4. Lancer le bot

```bash
python src/main.py
```


## 🛠 Technologies

- **Python 3.11**
- **py-cord 2.7.0**
- **python-dotenv**
- **Docker**


## 📄 Licence

Projet open-source — fais-en bon usage ❤️
