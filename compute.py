# compute.py
import sqlite3
from farasa.stemmer import FarasaStemmer

class SemanticSimilarity:
    def __init__(self, db_path='semantic_similarity.db'):
        self.db_path = db_path
        self.stemmer = FarasaStemmer(interactive=True)  # Initialize the Farasa stemmer

    def stem_word(self, word):
        """Stems a given Arabic word."""
        return self.stemmer.stem(word)


    # def get_ranking(self, word):
    #     """Retrieve the ranking for a word from the database."""
    #     conn = sqlite3.connect(self.db_path)
    #     cursor = conn.cursor()
    #     cursor.execute('SELECT ranking FROM word_rankings WHERE word = ?', (word,))
    #     result = cursor.fetchone()
    #     conn.close()
    #     return result[0] if result else None

    def get_ranking(self, guess, target_id):
        """Retrieve the ranking for a word with respect to a specific target word identified by target_id."""
        conn = sqlite3.connect(self.db_path)
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

    def get_top_rankings(self, target_id, limit=500):
        """Retrieve the top rankings for a specific target word from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Adjust the query to join the words and rankings tables, filtering by the given target_id
        cursor.execute('''
            SELECT w.word_text, r.ranking 
            FROM rankings r
            JOIN words w ON r.word_id = w.word_id
            WHERE r.target_id = ? 
            ORDER BY r.ranking ASC 
            LIMIT ?
        ''', (target_id, limit))
        results = cursor.fetchall()
        conn.close()
        return results

