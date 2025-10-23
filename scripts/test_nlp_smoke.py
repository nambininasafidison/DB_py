#!/usr/bin/env python3
"""
Test smoke pour le module NLP du projet.
- Entraîne le modèle pour 1 époque sur `src/config/dataset.json` (si présent)
- Sauvegarde les artefacts dans `train_output` (utilisé par l'initialisation)
- Tente de charger le modèle via `src/query/nlp_model.py` et exécute une traduction d'exemple
"""
import os
import sys
import json
import importlib

ROOT = os.path.dirname(os.path.dirname(__file__))
DATASET = os.path.join(ROOT, 'src', 'config', 'dataset.json')
OUT_DIR = os.path.join(ROOT, 'train_output')
MODEL_NAME = 'nlp_model.h5'

print('Dataset path:', DATASET)
if not os.path.exists(DATASET):
    print('Dataset not found at', DATASET)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from scripts.train_nlp import build_and_train
except Exception:
    import importlib.util
    train_path = os.path.join(ROOT, 'scripts', 'train_nlp.py')
    spec = importlib.util.spec_from_file_location('scripts.train_nlp', train_path)
    train_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(train_mod)
    build_and_train = getattr(train_mod, 'build_and_train')
rc = build_and_train(DATASET, OUT_DIR, epochs=1, batch_size=8, model_name=MODEL_NAME, target_loss=1.0)

with open(DATASET, 'r') as f:
    full_data = json.load(f)
small_n = min(200, len(full_data))
small_data = full_data[:small_n]
os.makedirs(OUT_DIR, exist_ok=True)
small_dataset_path = os.path.join(OUT_DIR, 'dataset_small.json')
with open(small_dataset_path, 'w') as f:
    json.dump(small_data, f)

print(f'Running smoke training on small dataset ({small_n} examples)')
rc = build_and_train(small_dataset_path, OUT_DIR, epochs=10, batch_size=8, model_name=MODEL_NAME, target_loss=1.0, learning_rate=0.001, step_epochs=2, max_total_epochs=20)
if rc != 0:
    print('Training script returned', rc)
    sys.exit(rc)

sys.path.insert(0, ROOT)
SRC_DIR = os.path.join(ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
try:
    import src.config.initialization as init
except Exception:
    try:
        import config.initialization as init
    except Exception as e:
        print('Failed to import initialization:', e)

nlp_model = None
import importlib
for modname in ('query.nlp_model', 'src.query.nlp_model'):
    try:
        mod = importlib.import_module(modname)
        nlp_model = getattr(mod, 'nlp_model')
        break
    except Exception:
        continue
if nlp_model is None:
    print('Failed to import nlp_model from known locations')
    sys.exit(3)

train_model_path = os.path.join(OUT_DIR, MODEL_NAME)
train_tokenizer = os.path.join(OUT_DIR, 'tokenizer.json')
train_mapping = os.path.join(OUT_DIR, 'sql_mapping.json')
train_examples = os.path.join(OUT_DIR, 'nlp_examples.json')

try:
    import config.config as conf
    conf.CONFIG['DATA_DIR'] = OUT_DIR
    conf.CONFIG['NLP_MODEL'] = train_model_path
    conf.CONFIG['TOKENIZER'] = train_tokenizer
    conf.CONFIG['SQL_MAPPING'] = train_mapping
except Exception:
    pass

print('Loading model from train_output...')
nlp_model.load(model_path=train_model_path)

if not nlp_model.model and not nlp_model.tokenizer:
    print('No model/tokenizer loaded. Check TensorFlow availability and artifacts.')
    sys.exit(4)

with open(DATASET, 'r') as f:
    data = json.load(f)
if not data:
    print('Empty dataset')
    sys.exit(5)

sample = data[0]
print('Sample query:', sample.get('query'))
res = nlp_model.process(sample.get('query'))
print('Translated SQL:', res)

if res:
    print('Smoke test success')
    sys.exit(0)
else:
    print('Smoke test: no translation produced')
    sys.exit(6)
