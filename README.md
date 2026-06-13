# 🧙 Eldoria - Bot Discord - ![Version](https://img.shields.io/github/v/tag/gass-an/Eldoria-Bot?label=Version&color=5865F2&sort=semver)

![Python](https://img.shields.io/static/v1?label=Python&message=3.11%2B&color=blueviolet&logo=python)
![py-cord](https://img.shields.io/static/v1?label=py-cord&message=2.7.0%2B&color=blueviolet&logo=python&logoColor=white)
![Discord](https://img.shields.io/static/v1?label=Discord&message=Bot&color=5865F2&logo=discord&logoColor=white)
![Docker](https://img.shields.io/static/v1?label=Docker&message=Ready&color=0db7ed&logo=docker&logoColor=white)  
![Status](https://img.shields.io/badge/⚙️%20Status-En%20développement-yellow)
![CI](https://github.com/gass-an/Eldoria-Bot/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/gass-an/Eldoria-Bot/branch/main/graph/badge.svg)](https://codecov.io/gh/gass-an/Eldoria-Bot)


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


## 🔗 Ajouter le bot à votre serveur

Vous pouvez inviter **Eldoria** sur votre serveur Discord en utilisant le lien ci-dessous.

➡️ [Inviter Eldoria sur votre serveur](https://discord.com/oauth2/authorize?client_id=1328953950656925736&permissions=2433870928&integration_type=0&scope=bot )

> ⚠️ Le bot utilise le principe du **moindre privilège** : aucune permission administrateur n’est requise.


<br> 
<br>
<br> 
<br> 
<br>

# 🛠️ Développement & installation

### 🧱 Prérequis

- Python **3.11+**
- Un bot Discord et son **TOKEN**
- (Optionnel) Docker



## 🚀 Lancer avec Docker Compose
> Méthode recommandée pour la production
### Prérequis
- Docker
- Docker Compose (plugin `docker compose`)

### 1. Configurer l'environnement
Crée un fichier **`.env`** à la racine du projet.  
Suivre le `.env.exemple` comme exemple.

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
git clone https://github.com/gass-an/Eldoria-Bot.git
cd Eldoria-Bot
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

Si tu veux lancer les tests localement, installe aussi les dépendances de dev :

```bash
pip install -r requirements-dev.txt
```

### 3. Configurer l’environnement
Crée un fichier **`.env`** à la racine du projet.  
Suivre le `.env.exemple` comme exemple.

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
