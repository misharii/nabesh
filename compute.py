# compute.py

import sqlite3
import numpy as np
from farasa.stemmer import FarasaStemmer



class SemanticSimilarity:
    def __init__(self, db_path='semantic_similarity.db'):
        self.db_path = db_path
        self.stemmer = FarasaStemmer(interactive=True)  # Initialize the Farasa stemmer

    def stem_word(self, word):
        """Stems a given Arabic word."""
        return self.stemmer.stem(word)

    def get_embedding(self, word):
        """Retrieve a precomputed embedding for a word from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT embedding FROM word_embeddings WHERE word = ?', (word,))
        result = cursor.fetchone()
        conn.close()
        if result:
            embedding = np.frombuffer(result[0], dtype=np.float32)
            return embedding
        else:
            return None

    def cosine_similarity(self, vec1, vec2):
        """Calculate the cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return dot_product / norm_product if norm_product else 0.0

    def get_similarity_score(self, word):
        """Retrieve the precomputed similarity score for a word from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT similarity FROM word_similarity WHERE word = ?', (word,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_ranking(self, word):
        """Retrieve the ranking for a word from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT ranking FROM word_rankings WHERE word = ?', (word,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_top_rankings(self, limit=1000):
        """Retrieve the top rankings from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT word, ranking FROM word_rankings ORDER BY ranking ASC LIMIT ?', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results
