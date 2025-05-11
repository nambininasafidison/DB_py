import json
import numpy as np
import config.config as conf
from config.language import LANGUAGES
from utils.logger_utils import print_error, print_response, print_success

from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer

class NLPModel:
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.model = None
        self.tokenizer = Tokenizer(num_words=20000, oov_token="<OOV>")
        self.sql_to_index = {}

    def train(self, training_data_path):
        try:
            with open(training_data_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            print_error(LANGUAGES[conf.global_language]["training_file_not_found"])
            return

        queries = [item["query"] for item in data]
        sql_commands = [item["sql"] for item in data]

        self.tokenizer.fit_on_texts(queries)
        sequences = self.tokenizer.texts_to_sequences(queries)
        padded_sequences = pad_sequences(sequences, maxlen=100, padding="post")

        self.sql_to_index = {sql: i for i, sql in enumerate(set(sql_commands))}
        indexed_sql = [self.sql_to_index[sql] for sql in sql_commands]

        model = Sequential([
            Embedding(input_dim=20000, output_dim=128, input_length=100),
            Bidirectional(LSTM(128, return_sequences=True)),
            Dropout(0.5),
            Bidirectional(LSTM(128)),
            Dense(128, activation="relu"),
            Dropout(0.5),
            Dense(len(self.sql_to_index), activation="softmax")
        ])
        model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

        print_response(LANGUAGES[conf.global_language]["training_in_progress"], "info")
        model.fit(padded_sequences, np.array(indexed_sql), epochs=10, batch_size=8)

        if self.model_path:
            model.save(self.model_path)
        with open(conf.CONFIG["TOKENIZER"], "w") as f:
            f.write(self.tokenizer.to_json())
        with open(conf.CONFIG["SQL_MAPPING"], "w") as f:
            json.dump(self.sql_to_index, f)

        print_success(LANGUAGES[conf.global_language]["model_trained"].format(model=self.model_path if self.model_path else "in-memory"))
        self.model = model

    def process(self, query):
        if not self.model:
            return ""
        seq = self.tokenizer.texts_to_sequences([query])
        padded_seq = pad_sequences(seq, maxlen=100, padding="post")
        pred = self.model.predict(padded_seq)
        predicted_index = np.argmax(pred)
        index_to_sql = {i: sql for sql, i in self.sql_to_index.items()}
        return index_to_sql.get(predicted_index, "")

nlp_model = NLPModel()