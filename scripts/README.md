# Montée de version

Le point d'entrée principal est `scripts/publish.py`. Les autres scripts du dossier sont
appelés automatiquement par celui-ci.

## Prérequis

- lancer la commande depuis la racine du dépôt ;
- être sur la branche `main` ;
- avoir un dépôt Git entièrement propre, sans fichier modifié ou non suivi ;
- avoir `main` local aligné avec `origin/main` ;
- utiliser une version au format `X.Y.Z`, par exemple `0.6.1` ;
- renseigner au moins une entrée sous `## [Unreleased]` dans `CHANGELOG.md` ;
- avoir les droits de push vers `origin`.

Le script lance `git fetch origin main --tags` et refuse de publier si `main` local n'est
pas exactement aligné avec `origin/main`. Dans ce cas, lancer :

```bash
git pull --rebase origin main
```

Il est recommandé de lancer les tests et de relire `CHANGELOG.md` avant la publication.
Le script ne le fait pas lui-même.

## Publication complète

```bash
python scripts/publish.py --to 0.6.1
```

Cette commande effectue successivement les actions suivantes :

1. vérifie que le dépôt est propre, sur `main`, et aligné avec `origin/main` ;
2. vérifie que le tag `v0.6.1` n'existe pas déjà localement ou sur `origin` ;
3. remplace la version dans `src/eldoria/version.py` ;
4. transforme la section `Unreleased` du changelog en section versionnée et datée ;
5. crée le commit `release(v0.6.1)` contenant uniquement le fichier de version et le changelog ;
6. pousse d'abord le commit sur `origin/main` ;
7. crée le tag `v0.6.1` ;
8. pousse le tag vers `origin`.

La publication est interrompue si la version est invalide, si `Unreleased` est vide, si le
repo n'est pas à jour, ou si le tag existe déjà avec une cible différente.

## Rollback

En publication complète, si une erreur arrive après la création du commit local mais avant
la fin de la publication, `publish.py` revient automatiquement à l'état Git initial :

- suppression du tag local créé si besoin ;
- `git reset --hard` vers le commit de départ.

Le rollback est local uniquement. Le script évite de pousser un tag tant que `main` n'a pas
été poussé avec succès.

## Idempotence

Le script peut être relancé sans créer de nouveau commit dans les états intermédiaires connus :

- si `HEAD` est déjà `release(vX.Y.Z)` mais que `main` n'a pas encore été poussé, la relance
  pousse `main`, crée le tag si besoin, puis pousse le tag ;
- si `HEAD` est déjà `release(vX.Y.Z)` et que `origin/main` pointe déjà dessus, la relance
  reprend à l'étape du tag ;
- si le tag local `vX.Y.Z` existe déjà et pointe vers `HEAD`, il est réutilisé ;
- si le tag distant `vX.Y.Z` existe déjà et pointe vers `HEAD`, la release est considérée
  comme déjà publiée.

En cas d'échec pendant la phase distante, le script ne rollback pas aveuglément :

- si aucun effet distant n'est détecté, il revient au commit de départ ;
- si `origin/main` ou un tag pointe déjà vers le commit de release, l'état local est conservé
  pour permettre une relance de la même commande.

Si l'état local est ambigu, le script refuse de deviner et demande de vérifier Git avant de
continuer.

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
- `release.py` pousse le commit de release, crée le tag, puis pousse le tag.

Pour une montée de version normale, utiliser uniquement `publish.py`.
