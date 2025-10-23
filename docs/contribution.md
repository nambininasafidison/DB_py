# Contribution

## Comment contribuer

1. Forkez le dépôt.
2. Créez une branche : `git checkout -b feature/ma-fonction`.
3. Codez et testez vos modifications.
4. Ajoutez des tests unitaires dans `tests/`.
5. Soumettez une Pull Request avec une description claire.

## Conventions

- **Style** : Suivez PEP 8.
- **Docstrings** : Obligatoires pour toutes les fonctions publiques.
- **Tests** : Ajoutez des tests unitaires pour chaque nouvelle fonctionnalité, y compris `TIME TRAVEL`, `DATA MASKING`, et `ROW LEVEL SECURITY`.

## Outils

- **Linter** : `flake8` pour vérifier le style de code.
- **Tests** : `pytest` pour exécuter les tests unitaires.

## Exemple de test

Ajoutez un fichier dans `tests/` :

```python
# filepath: tests/test_time_travel.py
def test_time_travel():
    result = db_system.time_travel_query("users", "2023-01-01T00:00:00", user)
    assert len(result) > 0
```

Exécutez les tests avec :

```bash
pytest
```

---

[← Sommaire](./index.md)
