import sqlite3
import numpy as np
import fasttext
import time
from flask import flash
from farasa.stemmer import FarasaStemmer

stemmer = FarasaStemmer(interactive=True)
model = None

def createDB(db_path='semantic_similarity.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS words (
        word_id INTEGER PRIMARY KEY AUTOINCREMENT,
        word_text TEXT UNIQUE
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS target (
        target_id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_text TEXT UNIQUE
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS rankings (
        word_id INTEGER,
        target_id INTEGER,
        ranking INTEGER,
        PRIMARY KEY (word_id, target_id),
        FOREIGN KEY (word_id) REFERENCES words(word_id),
        FOREIGN KEY (target_id) REFERENCES target(target_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password TEXT,
        last_login TEXT
    )''')

    cursor.execute('''INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)''', ('admin', 'nabesh'))
    conn.commit()
    conn.close()

def get_all_target_words(db_path='semantic_similarity.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT target_id, target_text FROM target ORDER BY target_id ASC")
    result = cursor.fetchall()
    conn.close()
    return result


def stem_word(word):
    """Stems a single word using Farasa stemmer."""
    return stemmer.stem(word)

def stem_words(target_words):
    """Stems a list of words."""
    return [stem_word(word) for word in target_words]


def reorder_target_ids(db_path='semantic_similarity.db'):
    global model
    if model is None:
        model, _ = load_model()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # استرجع كل الكلمات المستهدفة بالنص الأصلي قبل الحذف
    cursor.execute("SELECT target_text FROM target ORDER BY target_id ASC")
    targets = cursor.fetchall()

    # احذف كل البيانات لإعادة ترتيب الـ target_id من الصفر
    cursor.execute("DELETE FROM rankings")
    cursor.execute("DELETE FROM target")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='target'")
    conn.commit()

    # اقرأ قائمة الكلمات من الملف
    word_list = wordlistOpentxt()

    # أعد بناء كل target ورصد الكلمات المرتبطة بها
    for (target_text,) in targets:
        stemmed_target = stem_word(target_text)
        target_id = insert_target_word_with_rank_get_id(cursor, stemmed_target)
        target_embedding = model.get_word_vector(stemmed_target)
        similarities = cosine_similarity_sorted(model, stemmed_target, word_list, target_embedding)
        insert_words_with_rankings(cursor, similarities, target_id, start_rank=2)

    conn.commit()
    conn.close()





def load_model(modelPath='model/cc.ar.300.bin'):
    global model
    if model is None:
        model = fasttext.load_model(modelPath)
    return model, 0

def precompute_rankings(target_words, words, db_path='semantic_similarity.db'):
    model, model_load_time = load_model()
    start_time = time.time()
    createDB(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if isinstance(target_words, str):
        target_words = [target_words]

    for target_word in target_words:
        target_id = insert_target_word_with_rank_get_id(cursor, target_word)
        target_embedding = model.get_word_vector(target_word)
        similarities = cosine_similarity_sorted(model, target_word, words, target_embedding)
        # ✅ Insert the rest of the similar words starting from rank 2
        insert_words_with_rankings(cursor, similarities, target_id, start_rank=2)

    conn.commit()
    conn.close()
    end_time = time.time()
    computation_time = end_time - start_time
    flash(f'تم الانتهاء من الترتيب في {computation_time:.2f} ثانية للكلمات : {target_words} ', 'success')

    return model_load_time, computation_time


def insert_target_word_with_rank_get_id(cursor, target_word):
    # Insert or ignore into target table
    cursor.execute('INSERT OR IGNORE INTO target (target_text) VALUES (?)', (target_word,))
    cursor.execute('SELECT target_id FROM target WHERE target_text = ?', (target_word,))
    target_id = cursor.fetchone()[0]

    # Insert or ignore into words table
    cursor.execute('INSERT OR IGNORE INTO words (word_text) VALUES (?)', (target_word,))
    cursor.execute('SELECT word_id FROM words WHERE word_text = ?', (target_word,))
    word_id = cursor.fetchone()[0]

    # Insert or replace into rankings with rank 1
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


def get_ranking(stemmed_word, target_id, db_path='semantic_similarity.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.ranking
        FROM rankings r
        JOIN words w ON r.word_id = w.word_id
        WHERE w.word_text = ? AND r.target_id = ?
    """, (stemmed_word, target_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def insert_words_with_rankings(cursor, similarities, target_id, start_rank=2):
    for rank, (word, _) in enumerate(similarities, start=start_rank):
        cursor.execute('INSERT OR IGNORE INTO words (word_text) VALUES (?)', (word,))
        cursor.execute('SELECT word_id FROM words WHERE word_text = ?', (word,))
        word_id = cursor.fetchone()[0]
        cursor.execute('REPLACE INTO rankings (word_id, target_id, ranking) VALUES (?, ?, ?)', (word_id, target_id, rank))

def wordlistOpentxt(wordlistPath='wordlist/ar-wordlist-stemmed.txt'):
    word_list = []
    try:
        with open(wordlistPath, 'r', encoding='utf-8') as file:
            for line in file:
                word = line.strip()
                if word:
                    word_list.append(word)
    except FileNotFoundError:
        flash(f'Wordlist file not found at {wordlistPath}', 'danger')
    return word_list
