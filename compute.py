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

    def get_ranking(guess):
        conn = sqlite3.connect('semantic_similarity.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.ranking FROM rankings r
            JOIN words w ON r.word_id = w.word_id
            JOIN target t ON r.target_id = t.target_id
            WHERE w.word_text = ? AND t.target_text = ?
        ''', (guess, 'your_target_word'))  # 'your_target_word' should be replaced with the actual target word
        ranking = cursor.fetchone()
        conn.close()
        return ranking[0] if ranking else None

    def get_top_rankings(self, limit=500):
        """Retrieve the top rankings from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT word, ranking FROM word_rankings ORDER BY ranking ASC LIMIT ?', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results
