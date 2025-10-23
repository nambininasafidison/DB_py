import json
import os
import importlib
import config.config as conf
from config.language import LANGUAGES
from utils.logger_utils import print_error, print_response, print_success


class NLPModel:
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.sql_to_index = {}
        self.examples = []
        self._example_vectors = None
        self._vocab_size = 20000

    def train(self, training_data_path, epochs=10, batch_size=8):
        try:
            np = importlib.import_module('numpy')
            keras_text = importlib.import_module('tensorflow.keras.preprocessing.text')
            pad_sequences = importlib.import_module('tensorflow.keras.preprocessing.sequence').pad_sequences
            Tokenizer = keras_text.Tokenizer
            layers = importlib.import_module('tensorflow.keras.layers')
            Embedding = layers.Embedding
            LSTM = layers.LSTM
            Dense = layers.Dense
            Dropout = layers.Dropout
            Bidirectional = layers.Bidirectional
            Sequential = importlib.import_module('tensorflow.keras.models').Sequential
        except Exception:
            print_error(LANGUAGES[conf.global_language].get('tf_not_available', 'TensorFlow not available. Install TensorFlow to train the NLP model.'))
            return

        try:
            with open(training_data_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print_error(LANGUAGES[conf.global_language].get('training_file_not_found', 'Training data file not found'))
            return

        queries = [item['query'] for item in data]
        sqls = [item['sql'] for item in data]

        self.tokenizer = Tokenizer(num_words=self._vocab_size, oov_token='<OOV>')
        self.tokenizer.fit_on_texts(queries)
        sequences = self.tokenizer.texts_to_sequences(queries)
        X = pad_sequences(sequences, maxlen=100, padding='post')

        sql_set = list(sorted(set(sqls)))
        self.sql_to_index = {s: i for i, s in enumerate(sql_set)}
        y = importlib.import_module('numpy').array([self.sql_to_index[s] for s in sqls])

        model = Sequential([
            Embedding(input_dim=self._vocab_size, output_dim=128, input_length=100),
            Bidirectional(LSTM(128, return_sequences=True)),
            Dropout(0.5),
            Bidirectional(LSTM(128)),
            Dense(128, activation='relu'),
            Dropout(0.5),
            Dense(len(self.sql_to_index), activation='softmax')
        ])
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

        print_response(LANGUAGES[conf.global_language].get('training_in_progress', 'Training NLP model...'), 'info')
        model.fit(X, y, epochs=epochs, batch_size=batch_size)

        if conf.CONFIG.get('TOKENIZER'):
            with open(conf.CONFIG['TOKENIZER'], 'w') as f:
                f.write(self.tokenizer.to_json())
        if conf.CONFIG.get('SQL_MAPPING'):
            with open(conf.CONFIG['SQL_MAPPING'], 'w') as f:
                json.dump(self.sql_to_index, f)
        if self.model_path and hasattr(model, 'save'):
            model.save(self.model_path)

        if conf.CONFIG.get('DATA_DIR'):
            examples_path = os.path.join(conf.CONFIG['DATA_DIR'], 'nlp_examples.json')
            with open(examples_path, 'w') as f:
                json.dump([{'query': q, 'sql': s} for q, s in zip(queries, sqls)], f)

        self.model = model
        print_success(LANGUAGES[conf.global_language].get('model_trained', 'Model trained'))

    def load(self, model_path=None):
        model_path = model_path or conf.CONFIG.get('NLP_MODEL')
        tokenizer_path = conf.CONFIG.get('TOKENIZER')
        sql_map_path = conf.CONFIG.get('SQL_MAPPING')
        examples_path = os.path.join(conf.CONFIG.get('DATA_DIR', ''), 'nlp_examples.json')

        if tokenizer_path and os.path.exists(tokenizer_path):
            try:
                keras_text = importlib.import_module('tensorflow.keras.preprocessing.text')
                tokenizer_from_json = keras_text.tokenizer_from_json
                with open(tokenizer_path, 'r') as f:
                    self.tokenizer = tokenizer_from_json(f.read())
            except Exception:
                try:
                    kp = importlib.import_module('keras_preprocessing.text')
                    tokenizer_from_json = kp.tokenizer_from_json
                    with open(tokenizer_path, 'r') as f:
                        self.tokenizer = tokenizer_from_json(f.read())
                except Exception:
                    print_error(f'Failed to load tokenizer from {tokenizer_path}')

        if sql_map_path and os.path.exists(sql_map_path):
            try:
                with open(sql_map_path, 'r') as f:
                    self.sql_to_index = json.load(f)
            except Exception:
                print_error(f'Failed to load SQL mapping from {sql_map_path}')

        if os.path.exists(examples_path):
            try:
                with open(examples_path, 'r') as f:
                    self.examples = json.load(f)
            except Exception:
                print_error(f'Failed to load examples from {examples_path}')

        try:
            np = importlib.import_module('numpy')
            if self.tokenizer and self.examples:
                max_index = max(self.tokenizer.word_index.values()) if self.tokenizer.word_index else 0
                self._vocab_size = min(self._vocab_size, max_index + 1 if max_index > 0 else self._vocab_size)
                vecs = []
                for ex in self.examples:
                    seq = self.tokenizer.texts_to_sequences([ex['query']])[0]
                    v = np.zeros(self._vocab_size, dtype=float)
                    for idx in seq:
                        if 0 < idx < self._vocab_size:
                            v[idx] += 1.0
                    norm = np.linalg.norm(v)
                    if norm > 0:
                        v = v / norm
                    vecs.append(v)
                if vecs:
                    self._example_vectors = np.stack(vecs)
        except Exception:
            self._example_vectors = None

        if model_path and os.path.exists(model_path):
            try:
                keras_models = importlib.import_module('tensorflow.keras.models')
                self.model = keras_models.load_model(model_path)
                print_response('NLP model loaded', 'info')
            except Exception as e:
                print_error(f'Failed to load NLP model from {model_path}: {e}')

    def process(self, query):
        if self.model and self.tokenizer:
            try:
                pad_sequences = importlib.import_module('tensorflow.keras.preprocessing.sequence').pad_sequences
                np = importlib.import_module('numpy')
                seq = self.tokenizer.texts_to_sequences([query])
                padded = pad_sequences(seq, maxlen=100, padding='post')
                pred = self.model.predict(padded, verbose=0)
                predicted_index = int(np.argmax(pred))
                index_to_sql = {i: sql for sql, i in self.sql_to_index.items()}
                return index_to_sql.get(predicted_index, '')
            except Exception:
                return ''

        try:
            np = importlib.import_module('numpy')
            if self.tokenizer and self._example_vectors is not None and self.examples:
                seq = self.tokenizer.texts_to_sequences([query])[0]
                v = np.zeros(self._vocab_size, dtype=float)
                for idx in seq:
                    if 0 < idx < self._vocab_size:
                        v[idx] += 1.0
                norm = np.linalg.norm(v)
                if norm > 0:
                    v = v / norm
                sims = self._example_vectors.dot(v)
                best = int(np.argmax(sims))
                return self.examples[best].get('sql', '')
        except Exception:
            pass

        if self.examples:
            qset = set(query.lower().split())
            best = None
            best_score = 0
            for i, ex in enumerate(self.examples):
                s = set(ex.get('query', '').lower().split())
                score = len(qset & s)
                if score > best_score:
                    best_score = score
                    best = i
            if best is not None:
                return self.examples[best].get('sql', '')

        return ''


nlp_model = NLPModel()