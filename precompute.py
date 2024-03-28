# precompute.py

import sqlite3
import numpy as np
import fasttext
import time
from flask import flash
from farasa.stemmer import FarasaStemmer

stemmer = FarasaStemmer(interactive=True)  # Initialize the Farasa stemmer and hold in Global variable
model = None  # Global variable to hold the model

def createDB(db_path='semantic_similarity.db'):
    # Connect to the SQLite database at the specified path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create 'words' table
    cursor.execute('''CREATE TABLE IF NOT EXISTS words (
        word_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        word_text TEXT UNIQUE
    )''')

    # Create 'target' table
    cursor.execute('''CREATE TABLE IF NOT EXISTS target (
        target_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        target_text TEXT UNIQUE
    )''')

    # Create 'rankings' table
    cursor.execute('''CREATE TABLE IF NOT EXISTS rankings (
        word_id INTEGER, 
        target_id INTEGER, 
        ranking INTEGER, 
        PRIMARY KEY (word_id, target_id), 
        FOREIGN KEY (word_id) REFERENCES words(word_id), 
        FOREIGN KEY (target_id) REFERENCES target(target_id)
    )''')

    # Create 'admins' table
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY, 
        password TEXT, 
        last_login TEXT
    )''')

    # Insert default admin account
    cursor.execute('''INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)''', ('admin', 'nabesh'))

    # Commit changes and close connection
    conn.commit()
    conn.close()

def load_model(modelPath='model/cc.ar.300.bin/cc.ar.300.bin'):
    global model
    if model is None:
        begin_loading_model = time.time()
        model = fasttext.load_model(modelPath)
        end_loading_model = time.time()
        load_time = end_loading_model - begin_loading_model
        print(f"Loading the model completed in {load_time:.2f} seconds")
        flash(f'Loading the model completed in {load_time:.2f} seconds', 'info')
    else:
        load_time   = 0  # Model was already loaded
    return model, load_time


def precompute_rankings(target_words, words, db_path='semantic_similarity.db'):
    model, model_load_time = load_model()  # Now captures load time as well

    start_time = time.time()  # Start timing
    createDB(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Convert target_words to a list if it's a single string
    if isinstance(target_words, str):
        target_words = [target_words]

    for target_word in target_words:
        # Insert or ignore the target word and get its ID
        cursor.execute('INSERT OR IGNORE INTO target (target_text) VALUES (?)', (target_word,))
        cursor.execute('SELECT target_id FROM target WHERE target_text = ?', (target_word,))
        target_id = cursor.fetchone()[0]

        # Compute embedding for the target word
        target_embedding = model.get_word_vector(target_word)

        # Directly insert the target word with rank 1
        cursor.execute('INSERT OR IGNORE INTO words (word_text) VALUES (?)', (target_word,))
        cursor.execute('SELECT word_id FROM words WHERE word_text = ?', (target_word,))
        target_word_id = cursor.fetchone()[0]
        cursor.execute('REPLACE INTO rankings (word_id, target_id, ranking) VALUES (?, ?, 1)', (target_word_id, target_id))

        # Compute similarity for each non-target word and append
        similarities = []
        for word in [w for w in words if w != target_word]:
            word_embedding = model.get_word_vector(word)
            similarity = np.dot(target_embedding, word_embedding) / (np.linalg.norm(target_embedding) * np.linalg.norm(word_embedding))
            similarities.append((word, similarity))

        # Sort by similarity score in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Insert non-target words starting from rank 2
        for rank, (word, _) in enumerate(similarities, start=2):  # Start enumeration from 2
            cursor.execute('INSERT OR IGNORE INTO words (word_text) VALUES (?)', (word,))
            cursor.execute('SELECT word_id FROM words WHERE word_text = ?', (word,))
            word_id = cursor.fetchone()[0]
            cursor.execute('REPLACE INTO rankings (word_id, target_id, ranking) VALUES (?, ?, ?)', (word_id, target_id, rank))

    conn.commit()
    conn.close()
    end_time = time.time()  # End timing
    computation_time = end_time - start_time
    print(f"Ranking completed in {computation_time:.2f} seconds for targets: {target_words}")
    flash(f'Ranking completed in {computation_time:.2f} seconds for targets: {target_words}', 'success')

    return model_load_time, computation_time

def wordlistOpentxt(wordlistPath='wordlist/ar-wordlist-stemmed.txt'):
    word_list = []
    with open(wordlistPath, 'r', encoding='utf-8') as file:
        for line in file:
            word = line.strip()
            if word:
                word_list.append(word)
    return word_list

def stem_word(word):
    return stemmer.stem(word)

def stem_words(target_words):
    stemmed_target_words = []
    for word in target_words:
        stemmed_target_words.append(stemmer.stem(word))
    return stemmed_target_words

def get_ranking(guess, target_id, db_path="semantic_similarity.db"):
    """Retrieve the ranking for a word with respect to a specific target word identified by target_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
           SELECT r.ranking FROM rankings r
           JOIN words w ON r.word_id = w.word_id
           JOIN target t ON r.target_id = t.target_id
           WHERE w.word_text = ? AND t.target_id = ?
       ''', (guess, target_id))
    ranking = cursor.fetchone()
    conn.close()
    return ranking[0] if ranking else None

def get_all_target_words(db_path='semantic_similarity.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM target')
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result


if __name__ == "__main__":
    target_words = ["سيارة", "بحر", "مدينة", "قهوة", "مطار"] # Your target word/s

    stemmed_target_words = stem_words(target_words)

    precompute_rankings(stemmed_target_words, wordlistOpentxt())




