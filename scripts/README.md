# Montée de version

Le point d'entrée principal est `scripts/publish.py`. Les autres scripts du dossier sont
appelés automatiquement par celui-ci.

## Prérequis

- lancer la commande depuis la racine du dépôt ;
- utiliser une version au format `X.Y.Z`, par exemple `0.6.1` ;
- avoir un dépôt Git entièrement propre, sans fichier modifié ou non suivi ;
- renseigner au moins une entrée sous `## [Unreleased]` dans `CHANGELOG.md` ;
- être sur la branche à publier et avoir les droits de push vers `origin`.

Il est recommandé de lancer les tests et de relire `CHANGELOG.md` avant la publication.
Le script ne le fait pas lui-même.

## Publication complète

```bash
python scripts/publish.py --to 0.6.1
```

Cette commande effectue successivement les actions suivantes :

1. vérifie que le dépôt Git est propre ;
2. remplace la version dans `src/eldoria/version.py` ;
3. transforme la section `Unreleased` du changelog en section versionnée et datée ;
4. crée le commit `release(v0.6.1)` contenant uniquement le fichier de version et le changelog ;
5. crée le tag `v0.6.1` ;
6. pousse le commit courant, puis le tag vers `origin`.

La publication est interrompue si la version ne change pas, si `Unreleased` est vide ou
si le tag existe déjà.

## Préparation locale sans publication

```bash
python scripts/publish.py --to 0.6.1 --no-release
```

Cette variante exécute la montée de version, met à jour le changelog et crée le commit de
release. Elle ne crée aucun tag et n'effectue aucun push.

> Attention : `--no-release` n'est pas un mode simulation. Le fichier de version, le
> changelog et l'historique Git local sont réellement modifiés.

## Scripts appelés en interne

- `bump_version.py` met à jour `src/eldoria/version.py` ;
- `roll_changelog.py` archive la section `Unreleased` avec la date du jour ;
- `commit_release.py` crée le commit de release ;
- `release.py` crée le tag et pousse le commit et le tag.

Pour une montée de version normale, utiliser uniquement `publish.py`.
