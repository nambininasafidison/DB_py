# Installation

## Prérequis

### Logiciels

- **Python** : 3.8+ (recommandé : 3.11 pour une compatibilité optimale).
- **Redis** : Serveur opérationnel sur `localhost:6379` (configurable dans `config.py`).
- **SMTP (optionnel)** : Un serveur SMTP configuré pour l’envoi des codes OTP par email.

### Dépendances

Installez les bibliothèques nécessaires avec :

```bash
pip install -r requirements.txt
```

### Génération de la clé maître

Générez une clé maître pour le chiffrement :

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Ajoutez cette clé dans le fichier `config.py` sous la variable `MASTER_KEY_FILE`.

### Configuration avancée

Pour activer des fonctionnalités comme `TIME TRAVEL`, `DATA MASKING`, et `ROW LEVEL SECURITY`, assurez-vous que les dépendances suivantes sont installées :

- **Redis** : Pour le cache distribué.
- **Numba** : Pour l’optimisation parallèle.
- **TensorFlow** : Pour le parsing NLP des requêtes.
