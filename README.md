# Manuel d'Utilisation du SGBDR

## Introduction

Bienvenue dans le **SGBDR Python**, un système de gestion de bases de données relationnelles conçu pour surpasser des références comme PostgreSQL et MySQL en termes de performance, flexibilité et fonctionnalités avancées. Écrit en Python, ce projet intègre des technologies modernes pour répondre aux besoins des applications critiques :

- **Sécurité renforcée** : Chiffrement des données via `cryptography`, authentification multi-facteurs (MFA), et sessions sécurisées avec tokens.
- **Fiabilité** : Transactions conformes aux propriétés ACID pour garantir l’intégrité des données.
- **Performance** : Indexation optimisée avec des arbres B+, cache distribué via Redis, et exécution parallèle avec `numba`.
- **Flexibilité** : Réplication sécurisée sur SSL, support multilingue, et parsing de requêtes SQL ou en langage naturel grâce à un modèle NLP basé sur TensorFlow.
- **Interface utilisateur** : CLI interactive avec autocomplétion, historique, et affichage tabulaire des résultats.

Ce README vous guide à travers l’installation, la configuration, et l’utilisation de ce SGBDR.

---

## Prérequis

### Logiciels nécessaires

- **Python** : Version 3.8+ (recommandé : 3.11 pour compatibilité optimale avec les dépendances).
- **Serveur Redis** : Doit être installé et actif sur `localhost:6379` (configurable dans `config.py`).
- **SMTP (optionnel)** : Un serveur SMTP configuré pour l’envoi des codes OTP par email.

### Dépendances Python

Installez les bibliothèques requises avec :

```bash
pip install -r requirements.txt
```

## Entraînement du module NLP

Le module NLP du SGBDR permet de convertir automatiquement des requêtes en langage naturel en requêtes SQL.  
L’entraînement du modèle s’effectue en dehors du serveur principal, afin de ne pas alourdir le processus avec TensorFlow.

### Étapes d’entraînement

1. Créez un fichier JSON contenant une liste d’objets sous la forme :
   ```json
   { "query": "texte naturel", "sql": "requête SQL correspondante" }
   ```
2. Exécutez le script d’entraînement depuis la racine du projet :
   ```bash
   python3 scripts/train_nlp.py --data ./dataset.json --out-dir ./data_nlp --epochs 10 --model nlp_model.h5
   ```
3. Copiez les fichiers générés (`nlp_model.h5`, `tokenizer.json`, `sql_mapping.json`) vers le répertoire de données du SGBDR :
   ```bash
   mkdir -p ./data
   cp ./data_nlp/nlp_model.h5 ./data/tokenizer.json ./data/sql_mapping.json ./data/
   ```
4. Au démarrage, le SGBDR chargera automatiquement le modèle si ces fichiers sont présents  
   (voir `src/config/initialization.py` et `src/query/nlp_model.py`).

> **Remarque :** le script d’entraînement et le chargement du modèle utilisent TensorFlow.  
> Vous pouvez effectuer cette étape dans un environnement isolé (par exemple un conteneur Docker), puis simplement copier les artefacts nécessaires dans le répertoire de données du serveur.

---

## Mode allégé sans TensorFlow (option k-NN)

Pour les environnements où TensorFlow n’est pas souhaité en production, le SGBDR propose un mode alternatif reposant sur un algorithme léger de **recherche par similarité (k-NN)**.

### Fonctionnement

- Le script `scripts/train_nlp.py` génère également un fichier `nlp_examples.json`.
- En l’absence du modèle TensorFlow, le SGBDR :
  - utilise `tokenizer.json` pour vectoriser la requête en entrée,
  - exploite `nlp_examples.json` pour calculer la proximité avec les exemples connus,
  - et renvoie la requête SQL correspondante à l’exemple le plus pertinent.

Ce mode ne nécessite que `numpy` et le tokenizer — aucun chargement de modèle Keras.  
Il constitue une solution simple et rapide, adaptée aux jeux de requêtes courantes déjà couverts par le dataset d’entraînement.

---

## Documentation

Pour une description détaillée des modules, des API et des configurations avancées, consultez la [documentation complète](./docs/index.md).
