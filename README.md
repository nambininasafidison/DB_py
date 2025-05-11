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

Pour plus de détails, voir la [documentation complète](./docs/index.md)
