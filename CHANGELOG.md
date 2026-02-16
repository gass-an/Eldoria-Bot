# Changelog

Toutes les modifications notables du projet Eldoria sont documentées dans ce fichier.  
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/)  
et le versioning suit [Semantic Versioning](https://semver.org/lang/fr/).

---

## [Unreleased]

### Added
- Duels de mini-jeux pour miser de l'XP : disponible que pour Pierre-Feuille-Ciseaux (1 manche)
- Docstrings et typage strict
- Refacto Tests unitaires + Ajout tests unitaires manquant

### Changed
- Amélioration de l’affichage du terminal au lancement (banner + logs structurés)

### Fixed
- Réduction de la latence du menu d’aide en supprimant les ré-uploads inutiles de fichiers lors des éditions d’embed.

### Notes



## [0.5.1] – 2026-01-18

### Added
- Test unitaire sur l'ensemble du code

### Changed
- Refactorisation de l'architecture et des noms de fichiers

### Fixed
- Correction du daily reset pour l'xp en vocal (redémarrage ou non du bot)
- Changement de la couleur de l'embed : 0x00FFFF -> 0x3FA7C4


## [0.5.0] – 2026-01-17

### Added
- Architecture modulaire du bot (extensions / cogs)
- Système de persistance avec base de données SQLite
- Système de sauvegarde automatique configurable
- Messages de bienvenue configurables via JSON
- Commandes slash de base (structure prête pour extension)
- Support Docker avec `docker-compose`
- Gestion centralisée de la configuration via `.env`
- Mise en place du système de version

### Changed
- Organisation du projet clarifiée (`src/`, `data/`, `json/`)
- Chargement dynamique des extensions au démarrage
- Logs de démarrage plus lisibles

### Fixed
- Sécurisation du démarrage lorsque certaines variables d’environnement sont absentes
- Gestion des fuseaux horaires pour l’auto-save
- Correction de comportements silencieux en cas de configuration incomplète

### Notes
- Cette version marque une base stable du projet, mais reste en **v0.x**  
- Des changements structurels (config, DB, commandes) sont encore possibles avant la v1.0.0
