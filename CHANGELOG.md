# Changelog

Toutes les modifications notables du projet Eldoria sont documentées dans ce fichier.  
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/)  
et le versioning suit [Semantic Versioning](https://semver.org/lang/fr/).

---

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
