#!/usr/bin/env python3
"""
Train a simple NLP -> SQL classifier and save model/tokenizer/mapping to disk.

Usage:
  python3 scripts/train_nlp.py --data dataset.json --out-dir /path/to/out --epochs 10 --model nlp_model.h5

The dataset JSON should be a list of objects with keys: "query" (natural language) and "sql" (target SQL string).
"""
import argparse
import json
import os

def build_and_train(data_path, out_dir, epochs, batch_size, model_name, target_loss=None, learning_rate=0.001, step_epochs=None, max_total_epochs=None):
    try:
        import numpy as np
        from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, Bidirectional
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.preprocessing.sequence import pad_sequences
        from tensorflow.keras.preprocessing.text import Tokenizer
    except Exception as e:
        print('TensorFlow or dependencies not available:', e)
        return 2

    with open(data_path, 'r') as f:
        data = json.load(f)

    queries = [item['query'] for item in data]
    sqls = [item['sql'] for item in data]

    tokenizer = Tokenizer(num_words=20000, oov_token='<OOV>')
    tokenizer.fit_on_texts(queries)
    sequences = tokenizer.texts_to_sequences(queries)
    X = pad_sequences(sequences, maxlen=100, padding='post')

    sql_set = list(sorted(set(sqls)))
    sql_to_index = {s: i for i, s in enumerate(sql_set)}
    y = np.array([sql_to_index[s] for s in sqls])

    model = Sequential([
        Embedding(input_dim=20000, output_dim=128, input_length=100),
        Bidirectional(LSTM(128, return_sequences=True)),
        Dropout(0.5),
        Bidirectional(LSTM(128)),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(len(sql_set), activation='softmax')
    ])
    # Configure optimizer with optional learning rate
    try:
        from tensorflow.keras.optimizers import Adam
        optimizer = Adam(learning_rate=learning_rate)
    except Exception:
        optimizer = 'adam'
    model.compile(optimizer=optimizer, loss='sparse_categorical_crossentropy', metrics=['accuracy'])

    callbacks = []
    if target_loss is not None:
        try:
            from tensorflow.keras.callbacks import Callback

            class LossThresholdCallback(Callback):
                def __init__(self, threshold):
                    super().__init__()
                    self.threshold = threshold

                def on_epoch_end(self, epoch, logs=None):
                    loss = None
                    if logs is not None:
                        loss = logs.get('loss')
                    if loss is not None and loss < self.threshold:
                        print(f"Loss {loss:.4f} < {self.threshold}, stopping training at epoch {epoch+1}.")
                        self.model.stop_training = True

            callbacks.append(LossThresholdCallback(target_loss))
        except Exception:
            pass

    try:
        from tensorflow.keras.callbacks import ReduceLROnPlateau, ModelCheckpoint
        reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.5, patience=2, min_lr=1e-6, verbose=1)
        callbacks.append(reduce_lr)
        os.makedirs(out_dir, exist_ok=True)
        checkpoint_path = os.path.join(out_dir, model_name + '.best')
        checkpoint_cb = ModelCheckpoint(checkpoint_path, monitor='loss', save_best_only=True, save_weights_only=False)
        callbacks.append(checkpoint_cb)
    except Exception:
        pass

    if target_loss is not None and step_epochs and max_total_epochs and max_total_epochs > 0:
        total_trained = 0
        achieved = False
        while total_trained < max_total_epochs:
            remaining = max_total_epochs - total_trained
            run_epochs = min(step_epochs, remaining)
            history = model.fit(X, y, epochs=run_epochs, batch_size=batch_size, callbacks=callbacks)
            total_trained += run_epochs
            last_loss = None
            if 'loss' in history.history:
                last_loss = history.history['loss'][-1]
            if last_loss is not None:
                print(f'After {total_trained} epochs, loss={last_loss:.4f}')
                if last_loss < target_loss:
                    achieved = True
                    print(f'Target loss {target_loss} reached (loss={last_loss:.4f}). Stopping training.')
                    break
        if not achieved:
            print(f'Max total epochs {max_total_epochs} reached; last loss={last_loss}')
    else:
        model.fit(X, y, epochs=epochs, batch_size=batch_size, callbacks=callbacks)

    os.makedirs(out_dir, exist_ok=True)
    model_path = os.path.join(out_dir, model_name)
    tokenizer_path = os.path.join(out_dir, 'tokenizer.json')
    mapping_path = os.path.join(out_dir, 'sql_mapping.json')

    model.save(model_path)
    with open(tokenizer_path, 'w') as f:
        f.write(tokenizer.to_json())
    with open(mapping_path, 'w') as f:
        json.dump(sql_to_index, f)
    examples_path = os.path.join(out_dir, 'nlp_examples.json')
    with open(examples_path, 'w') as f:
        json.dump(data, f)

    print('Saved model to', model_path)
    print('Saved tokenizer to', tokenizer_path)
    print('Saved mapping to', mapping_path)
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True, help='Path to dataset JSON')
    p.add_argument('--out-dir', default='./train_output', help='Output directory for model/tokenizer/mapping (default: ./train_output)')
    p.add_argument('--epochs', type=int, default=10)
    p.add_argument('--batch-size', type=int, default=8)
    p.add_argument('--target-loss', type=float, default=None, help='Stop training early when loss < target')
    p.add_argument('--learning-rate', type=float, default=0.001, help='Initial learning rate for optimizer')
    p.add_argument('--step-epochs', type=int, default=None, help='Train in small steps of N epochs and check target loss')
    p.add_argument('--max-total-epochs', type=int, default=None, help='Maximum total epochs when using step-epochs')
    p.add_argument('--model', default='nlp_model.h5', help='Saved model filename')
    args = p.parse_args()

    rc = build_and_train(
        args.data,
        args.out_dir,
        args.epochs,
        args.batch_size,
        args.model,
        target_loss=args.target_loss,
        learning_rate=args.learning_rate,
        step_epochs=args.step_epochs,
        max_total_epochs=args.max_total_epochs
    )
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
