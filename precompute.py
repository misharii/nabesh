# precompute_embeddings.py

import sqlite3
import numpy as np
import fasttext
import time


# Load your pre-trained FastText model
model = fasttext.load_model('model/cc.ar.300.bin/cc.ar.300.bin')

def precompute_rankings(target_word, words, db_path='semantic_similarity.db'):
    start_time = time.time()  # Start timing
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing data in the word_rankings table
    cursor.execute('DELETE FROM word_rankings')

    # Create a table for storing words and their rankings
    cursor.execute('''CREATE TABLE IF NOT EXISTS word_rankings
                      (word TEXT PRIMARY KEY, ranking INTEGER)''')

    # Compute embedding for the target word
    target_embedding = model.get_word_vector(target_word)

    # Compute similarity and collect scores
    similarities = []
    for word in words:
        word_embedding = model.get_word_vector(word)
        similarity = np.dot(target_embedding, word_embedding) / (np.linalg.norm(target_embedding) * np.linalg.norm(word_embedding))
        similarities.append((word, similarity))

    # Sort by similarity score in descending order
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Store the rankings
    for rank, (word, _) in enumerate(similarities, start=1):
        cursor.execute('REPLACE INTO word_rankings (word, ranking) VALUES (?, ?)', (word, rank))

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    end_time = time.time()  # End timing
    print(f"Ranking completed in {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    target_word = "هاتف"  # Your target word
    word_list = []
    with open('wordlist/ar-wordlist-stemmed.txt', 'r', encoding='utf-8') as file:
        for line in file:
            # Strip newline character and any leading/trailing whitespace
            word = line.strip()
            if word:  # Make sure the line is not empty
                word_list.append(word)

    start_time_open = time.time()  # Start timing
    precompute_rankings(target_word, word_list)
    end_time_open = time.time()  # End timing
    print(f"total time completed in {end_time_open - start_time_open:.2f} seconds")
