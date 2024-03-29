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
        flash(f'اكتمل تحميل نموذج "fasttext" في:{load_time:.2f} ثانية ', 'info')
    else:
        load_time   = 0  # Model was already loaded
    return model, load_time




def insert_target_word_with_rank_get_id(cursor, target_word):
    # Insert or ignore the target word in the 'target' table
    cursor.execute('INSERT OR IGNORE INTO target (target_text) VALUES (?)', (target_word,))
    # Retrieve the ID of the target word
    cursor.execute('SELECT target_id FROM target WHERE target_text = ?', (target_word,))
    target_id = cursor.fetchone()[0]

    # Insert or ignore the target word in the 'words' table
    cursor.execute('INSERT OR IGNORE INTO words (word_text) VALUES (?)', (target_word,))
    # Retrieve the ID of the word from 'words' table
    cursor.execute('SELECT word_id FROM words WHERE word_text = ?', (target_word,))
    word_id = cursor.fetchone()[0]
    # Insert or replace the ranking for the target word with rank 1
    cursor.execute('REPLACE INTO rankings (word_id, target_id, ranking) VALUES (?, ?, 1)', (word_id, target_id))

    return target_id


def cosine_similarity_sorted(model, target_word, words, target_embedding):
    similarities = []
    for word in [w for w in words if w != target_word]:
        word_embedding = model.get_word_vector(word)
        similarity = np.dot(target_embedding, word_embedding) / (np.linalg.norm(target_embedding) * np.linalg.norm(word_embedding))
        similarities.append((word, similarity))
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities

def insert_words_with_rankings(cursor, similarities, target_id, start_rank=2):
    for rank, (word, _) in enumerate(similarities, start=start_rank):
        cursor.execute('INSERT OR IGNORE INTO words (word_text) VALUES (?)', (word,))
        cursor.execute('SELECT word_id FROM words WHERE word_text = ?', (word,))
        word_id = cursor.fetchone()[0]
        cursor.execute('REPLACE INTO rankings (word_id, target_id, ranking) VALUES (?, ?, ?)', (word_id, target_id, rank))


def precompute_rankings(target_words, words, db_path='semantic_similarity.db'):
    model, model_load_time = load_model()  # Load fasttext for embedding calculation
    start_time = time.time()
    createDB(db_path)  # Initialize the database
    conn = sqlite3.connect(db_path)  # Connect to the database
    cursor = conn.cursor()  # Create a database cursor for executing SQL commands

    # Ensure target_words is a list
    if isinstance(target_words, str):
        target_words = [target_words]

    for target_word in target_words:  # Iterate through each target word

        # Insert the target word and get its unique ID from the database
        target_id = insert_target_word_with_rank_get_id(cursor, target_word)

        # Compute the embedding vector for the target word using the model
        target_embedding = model.get_word_vector(target_word)

        # Compute and sort similarities of all other words to the target word
        similarities = cosine_similarity_sorted(model, target_word, words, target_embedding)

        # Insert words and their similarity rankings into the database
        insert_words_with_rankings(cursor, similarities, target_id)

    conn.commit()  # Commit all database transactions
    conn.close()  # Close the database connection
    end_time = time.time()  # End timing
    computation_time = end_time - start_time
    flash(f'تم الانتهاء من الترتيب في{computation_time:.2f} ثانية للكلمات : {target_words} ', 'success')

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




