
# Configuration Avancée

## Fichier principal

Modifiez `src/config/config.py` pour personnaliser le SGBDR.

### Paramètres clés

- `REDIS_HOST` : "localhost" (adresse du serveur Redis).
- `REDIS_PORT` : 6379 (port Redis).
- `ENCRYPTION_KEY` : Clé Fernet (générez avec `Fernet.generate_key()`).
- `SMTP_SERVER` : "smtp.gmail.com" (serveur SMTP, optionnel).
- `SMTP_PORT` : 587 (port SMTP).
- `SMTP_USER` : Votre email.
- `SMTP_PASSWORD` : Mot de passe ou clé d’app.

### Exemple

```python
# src/config/config.py
ENCRYPTION_KEY = b'votre_clé_générée'
REDIS_HOST = "localhost"
REDIS_PORT = 6379
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "user@example.com"
SMTP_PASSWORD = "votre_mot_de_passe"
```

### Configuration du SMTP

Pour activer l’envoi des OTP par email, configurez les paramètres SMTP dans `config.py` :

```python
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "votre_email@gmail.com"
SMTP_PASSWORD = "votre_mot_de_passe"
```

---

[← Sommaire](./index.md)
