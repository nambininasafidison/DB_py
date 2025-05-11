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

- **Autocomplétion** : Appuyez sur Tab.
- **Historique** : Utilisez les flèches haut/bas.
- **Sortie** : Tapez `EXIT` ou utilisez `Ctrl+D`.

## Commandes

### Bases de données

- `CREATE DATABASE mydb` : Crée une base de données.
- `DROP DATABASE mydb` : Supprime une base de données.
- `USE mydb` : Sélectionne la base de données active.

### Tables

- `CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50))` : Crée une table.
- `DROP TABLE users` : Supprime une table.
- `ALTER TABLE users ADD age INT` : Ajoute une colonne.
- `TRUNCATE TABLE users` : Vide la table.
- `DESCRIBE users` : Affiche la structure de la table.

### Données

- `INSERT INTO users (id, name) VALUES (1, 'Alice')` : Insère une ligne.
- `UPDATE users SET name='Bob' WHERE id=1` : Met à jour des données.
- `SELECT * FROM users WHERE id=1` : Récupère des données.
- `SELECT * FROM users JOIN roles ON users.role_id=roles.id` : Effectue une jointure.

### Transactions

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

### Avancées

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

## Exemple

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
