# Revenir au sommaire ← [Sommaire](./index.md)

# Manuel d’Utilisation

## Démarrage

Lancez le SGBDR avec :

```bash
python main.py -u admin -p <motdepasse>
```

Ou sans arguments pour le mode interactif :

```bash
python main.py
```

## Authentification

1. Entrez votre nom d’utilisateur et mot de passe.
2. Saisissez le code OTP (affiché en mode test ou envoyé par email si le serveur SMTP est configuré).
3. Une session est créée avec un token.

## Interface CLI

### Prompt :

```text
✓ Welcome, admin!
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ λ Database Pro [Version 1.2.1] (lang='en') ┃ Ctrl+D pour quitter
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ ➤ Enter command
┃ ➜ admin@None $
```

- **Autocomplétion** : Appuyez sur Tab pour compléter les commandes ou noms de tables/colonnes.
- **Historique** : Utilisez les flèches haut/bas pour naviguer dans l’historique des commandes.
- **Sortie** : Tapez `EXIT` ou utilisez `Ctrl+D` pour quitter la session.

## Commandes

### Bases de données

- `CREATE DATABASE mydb` : Crée une nouvelle base de données nommée `mydb`.
- `DROP DATABASE mydb` : Supprime la base de données `mydb` et toutes ses tables.
- `USE mydb` : Sélectionne la base de données active sur laquelle opérer.
- `SHOW DATABASES` : Affiche la liste de toutes les bases de données existantes.

### Tables

- `CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50))` : Crée une table `users` avec les colonnes spécifiées.
- `DROP TABLE users` : Supprime la table `users` de la base de données active.
- `ALTER TABLE users ADD age INT` : Ajoute une colonne `age` de type `INT` à la table `users`.
- `ALTER TABLE users DROP COLUMN age` : Supprime la colonne `age` de la table `users`.
- `TRUNCATE TABLE users` : Vide toutes les données de la table `users` sans supprimer la structure.
- `DESCRIBE users` : Affiche la structure (schéma) de la table `users`.
- `SHOW TABLES` : Affiche la liste des tables de la base de données active.

### Données

- `INSERT INTO users (id, name) VALUES (1, 'Alice')` : Insère une nouvelle ligne dans la table `users`.
- `UPDATE users SET name='Bob' WHERE id=1` : Met à jour la colonne `name` de la ligne où `id=1` dans la table `users`.
- `DELETE FROM users WHERE id=1` : Supprime la ligne où `id=1` dans la table `users`.
- `SELECT * FROM users` : Récupère toutes les lignes de la table `users`.
- `SELECT * FROM users WHERE id=1` : Récupère les lignes où `id=1` dans la table `users`.
- `SELECT * FROM users JOIN roles ON users.role_id=roles.id` : Effectue une jointure entre `users` et `roles`.

### Transactions

- `BEGIN` : Démarre une transaction.
- `COMMIT` : Valide la transaction en cours.
- `ROLLBACK` : Annule la transaction en cours.

#### Savepoint

```sql
SAVEPOINT savepoint_name;
```

Crée un point de sauvegarde dans une transaction.

#### Rollback to Savepoint

```sql
ROLLBACK TO SAVEPOINT savepoint_name;
```

Reviens à un point de sauvegarde spécifique.

#### Release Savepoint

```sql
RELEASE SAVEPOINT savepoint_name;
```

Supprime un point de sauvegarde.

### Gestion des utilisateurs

- `CREATE USER bob IDENTIFIED BY 'password'` : Crée un nouvel utilisateur `bob` avec le mot de passe spécifié.
- `ALTER USER bob IDENTIFIED BY 'newpassword'` : Modifie le mot de passe de l’utilisateur `bob`.
- `DROP USER bob` : Supprime l’utilisateur `bob`.
- `GRANT SELECT ON mydb.users TO bob` : Accorde le droit de lecture sur la table `users` de la base `mydb` à l’utilisateur `bob`.
- `REVOKE SELECT ON mydb.users FROM bob` : Retire le droit de lecture sur la table `users` de la base `mydb` à l’utilisateur `bob`.

### Sauvegarde et restauration

- `BACKUP mydb TO '/chemin/backupfile'` : Sauvegarde la base de données `mydb` vers le fichier spécifié.
- `RESTORE mydb FROM '/chemin/backupfile'` : Restaure la base de données `mydb` à partir du fichier de sauvegarde.

### Langue

- `SET LANGUAGE fr` : Définit la langue de l’interface en français.
- `SET LANGUAGE en` : Définit la langue de l’interface en anglais.

### Intelligence Artificielle (NLP)

- `TRAIN NLP MODEL` : Entraîne un modèle NLP sur les données disponibles.

### Commandes avancées

#### Full Outer Join

```sql
SELECT * FROM table1 FULL OUTER JOIN table2 ON table1.id = table2.id;
```

Combine les lignes des deux tables, incluant les correspondances et les non-correspondances.

#### Division

```sql
SELECT * FROM table1 DIVISION table2;
```

Renvoie les lignes de `table1` qui correspondent à toutes les lignes de `table2`.

#### Time Travel

```sql
SELECT * FROM users AS OF '2023-01-01T00:00:00';
```

Permet d’interroger les données historiques à une date donnée.

#### Data Masking

```sql
ALTER TABLE users ADD DATA MASKING ON email USING 'MASK_EMAIL';
```

Masque dynamiquement les colonnes sensibles.

#### Row Level Security

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

Active la sécurité au niveau des lignes pour des politiques d’accès granulaires.

#### Query Hints

```sql
SELECT /*+ USE INDEX */ * FROM users;
```

Optimise les requêtes en utilisant des indices.

#### MERGE

```sql
MERGE INTO target_table USING source_table ON target_table.id = source_table.id
WHEN MATCHED THEN UPDATE SET target_table.name = source_table.name
WHEN NOT MATCHED THEN INSERT (id, name) VALUES (source_table.id, source_table.name);
```

Effectue des opérations d’UPSERT (mise à jour ou insertion).

#### Window Functions

```sql
SELECT id, ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank
FROM employees;
```

Calcule des rangs ou des agrégats sur des partitions de données.

#### JSON_TABLE

```sql
SELECT * FROM users, JSON_TABLE(users.json_column, '$.path' COLUMNS (col1 INT PATH '$.field1'));
```

Extrait et manipule des données JSON.

#### Recursive CTE

```sql
WITH RECURSIVE cte_name AS (
    SELECT id, parent_id FROM employees WHERE parent_id IS NULL
    UNION ALL
    SELECT e.id, e.parent_id FROM employees e
    INNER JOIN cte_name c ON e.parent_id = c.id
)
SELECT * FROM cte_name;
```

Permet de parcourir des structures hiérarchiques.

## Exemples d’utilisation

### Création et manipulation de base de données

```sql
CREATE DATABASE testdb;
USE testdb;
CREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(50));
INSERT INTO employees (id, name) VALUES (1, 'Alice');
SELECT * FROM employees;
```

### Sortie :

```text
+----+-------+
| id | name  |
+----+-------+
|  1 | Alice |
+----+-------+
```

### Transactions avec savepoint

```sql
BEGIN;
INSERT INTO employees (id, name) VALUES (2, 'Bob');
SAVEPOINT sp1;
INSERT INTO employees (id, name) VALUES (3, 'Charlie');
ROLLBACK TO SAVEPOINT sp1;
COMMIT;
SELECT * FROM employees;
```

### Gestion des utilisateurs

```sql
CREATE USER bob IDENTIFIED BY 'password';
GRANT SELECT ON testdb.employees TO bob;
REVOKE SELECT ON testdb.employees FROM bob;
DROP USER bob;
```

### Sauvegarde et restauration

```sql
BACKUP testdb TO '/tmp/backupfile';
RESTORE testdb FROM '/tmp/backupfile';
```

### Utilisation de fonctionnalités avancées

```sql
SELECT * FROM employees AS OF '2024-01-01T00:00:00';
ALTER TABLE employees ADD DATA MASKING ON name USING 'MASK_NAME';
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
```

Pour plus de détails sur chaque commande, consultez la documentation ou utilisez l’autocomplétion dans le CLI.

### Utilisation détaillée des fonctionnalités avancées

#### 1. Time Travel (Voyage temporel)

Permet d’interroger l’état d’une table à une date/heure passée. Utile pour l’audit, la conformité ou l’analyse d’évolution.

**Syntaxe :**

```sql
SELECT * FROM <table> AS OF '<timestamp ISO8601>';
```

**Exemple :**

```sql
SELECT * FROM employees AS OF '2024-01-01T00:00:00';
```

**Résultat attendu :**
Affiche les données telles qu’elles étaient à la date spécifiée.

**Remarques :**

- Les opérations de Time Travel sont possibles uniquement si l’historisation est activée dans la configuration.
- Les requêtes Time Travel sont plus lentes car elles lisent les fichiers d’historique.

#### 2. Data Masking (Masquage de données)

Permet de masquer dynamiquement des colonnes sensibles (ex : email, téléphone) pour certains utilisateurs ou rôles.

**Syntaxe :**

```sql
ALTER TABLE <table> ADD DATA MASKING ON <colonne> USING '<masque>';
```

**Exemple :**

```sql
ALTER TABLE users ADD DATA MASKING ON email USING 'MASK_EMAIL';
SELECT email FROM users;
```

**Résultat attendu :**
Les emails sont affichés masqués (ex : a\*\*\*\*@domaine.com) pour les utilisateurs non autorisés.

**Remarques :**

- Plusieurs types de masques sont disponibles : `MASK_EMAIL`, `MASK_PHONE`, etc.
- Le masquage s’applique automatiquement selon la politique de sécurité.

#### 3. Row Level Security (Sécurité au niveau des lignes)

Active des politiques d’accès granulaires : chaque utilisateur ne voit que les lignes auxquelles il a droit.

**Syntaxe :**

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
```

**Exemple :**

```sql
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
SELECT * FROM employees;
```

**Résultat attendu :**
Chaque utilisateur ne voit que ses propres lignes ou celles autorisées par la politique définie.

**Remarques :**

- Les politiques sont configurables via des triggers ou des règles dans la base.
- Idéal pour les applications multi-tenant ou la confidentialité accrue.

#### 4. MERGE (UPSERT)

Permet de fusionner des données : met à jour si la ligne existe, insère sinon.

**Syntaxe :**

```sql
MERGE INTO <cible> USING <source> ON <condition>
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT (...)
```

**Exemple :**

```sql
MERGE INTO employees USING new_employees ON employees.id = new_employees.id
WHEN MATCHED THEN UPDATE SET employees.name = new_employees.name
WHEN NOT MATCHED THEN INSERT (id, name) VALUES (new_employees.id, new_employees.name);
```

**Résultat attendu :**
Les employés existants sont mis à jour, les nouveaux sont insérés.

#### 5. Window Functions (Fonctions de fenêtre)

Permettent des calculs avancés sur des partitions de données (classements, cumuls, etc).

**Syntaxe :**

```sql
SELECT <colonnes>, ROW_NUMBER() OVER (PARTITION BY <col> ORDER BY <col2>) AS rang
FROM <table>;
```

**Exemple :**

```sql
SELECT id, ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rang
FROM employees;
```

**Résultat attendu :**
Classe chaque employé par salaire décroissant dans son département.

#### 6. JSON_TABLE

Permet d’extraire et de manipuler des données structurées en JSON dans une colonne.

**Syntaxe :**

```sql
SELECT * FROM <table>, JSON_TABLE(<colonne_json>, '<chemin>' COLUMNS (...));
```

**Exemple :**

```sql
SELECT * FROM users, JSON_TABLE(users.json_column, '$.path' COLUMNS (col1 INT PATH '$.field1'));
```

**Résultat attendu :**
Crée des colonnes virtuelles à partir des champs JSON.

#### 7. Recursive CTE (WITH RECURSIVE)

Permet de parcourir des structures hiérarchiques (ex : arbres, organisations).

**Syntaxe :**

```sql
WITH RECURSIVE nom_cte AS (
    requête_base
    UNION ALL
    requête_récursive
)
SELECT * FROM nom_cte;
```

**Exemple :**

```sql
WITH RECURSIVE org_chart AS (
    SELECT id, manager_id FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.id, e.manager_id FROM employees e
    INNER JOIN org_chart o ON e.manager_id = o.id
)
SELECT * FROM org_chart;
```

**Résultat attendu :**
Affiche toute la hiérarchie de l’organisation.

#### 8. Query Hints (Indications d’optimisation)

Permet de guider l’optimiseur pour utiliser un index ou une stratégie spécifique.

**Syntaxe :**

```sql
SELECT /*+ USE INDEX */ * FROM <table>;
```

**Exemple :**

```sql
SELECT /*+ USE INDEX */ * FROM users WHERE email = 'a@b.com';
```

**Résultat attendu :**
L’index est utilisé pour accélérer la requête.

#### 9. NLP et requêtes en langage naturel

Le SGBDR peut interpréter des requêtes en français ou anglais grâce au modèle NLP intégré.

**Exemple :**

```
Montre-moi tous les employés du département RH embauchés après 2022
```

**Résultat attendu :**
La requête est traduite automatiquement en SQL et exécutée.

**Remarques :**

- Entraînez le modèle avec `TRAIN NLP MODEL` pour améliorer la compréhension.
- Le NLP fonctionne pour les requêtes simples et courantes.

---

Pour chaque fonctionnalité avancée, consultez la documentation technique pour les limitations, les options de configuration et les exemples d’erreurs courantes.
