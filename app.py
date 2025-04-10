from flask import Flask, request, render_template, session, redirect, url_for, flash , jsonify
from functools import wraps
from precompute import *
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = '123'
app.config['SESSION_PERMANENT'] = True
createDB()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/adminPanel', methods=['GET', 'POST'])
@login_required
def adminPanel():
    all_target_words = get_all_target_words()
    top_words_dict = {}

    try:
        conn = sqlite3.connect('semantic_similarity.db')
        cursor = conn.cursor()
        for target_id, _ in all_target_words:
            cursor.execute('''
                SELECT w.word_text, r.ranking
                FROM rankings r
                JOIN words w ON r.word_id = w.word_id
                WHERE r.target_id = ?
                ORDER BY r.ranking ASC
                LIMIT 10
            ''', (target_id,))
            top_words = cursor.fetchall()
            top_words_dict[target_id] = top_words
        conn.close()
    except Exception as e:
        flash(f'An error occurred while fetching top words: {e}', 'danger')

    # ✅ Handle POST: Add new target words
    if request.method == 'POST':
        word_count = int(request.form.get('wordCount', 0))
        target_words_list = [request.form.get(f'word{i}') for i in range(word_count) if request.form.get(f'word{i}')]
        if not target_words_list:
            flash('لم يتم إدخال أي كلمات.', 'danger')
            return redirect(url_for('adminPanel'))

        stemmed_target_words = stem_words(target_words_list)
        word_list = wordlistOpentxt()

        try:
            model_load_time, computation_time = precompute_rankings(stemmed_target_words, word_list)
            flash('تمت إضافة الكلمات بنجاح!', 'success')
            return redirect(url_for('adminPanel'))
        except Exception as e:
            flash(f'حدث خطأ أثناء الترتيب: {e}', 'danger')

    return render_template('adminPanel.html', all_target_words=all_target_words, top_words_dict=top_words_dict)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('adminPanel'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        createDB()
        conn = sqlite3.connect('semantic_similarity.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username=? AND password=?", (username, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session['user_id'] = admin[0]
            session['username'] = username
            session['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            next_page = request.args.get('next') or url_for('adminPanel')
            return redirect(next_page)
        else:
            flash('Login failed. Please check your username and password.', 'warning')

    return render_template('login.html')

@app.route('/')
def index():
    conn = sqlite3.connect('semantic_similarity.db')
    cursor = conn.cursor()
    cursor.execute('SELECT target_id, target_text FROM target ORDER BY target_id ASC')
    games = cursor.fetchall()
    conn.close()
    print("🌀 Session at index route:", dict(session))
    guesses = session.get('guesses', [])
    sorted_guesses = sorted(guesses, key=lambda x: x[1])
    message = session.pop('message', None) if 'message' in session else None
    return render_template('index.html', guesses=sorted_guesses, message=message, games=games)

@app.route('/start/<int:target_id>', methods=['GET'])
def start_game(target_id):
    session['target_id'] = target_id
    session['guesses'] = []
    session['recent_ranking'] = ""
    session.pop('winner', None)  # ✅ Clear win status
    return redirect(url_for('index'))

@app.route('/guess', methods=['POST'])
def guess():
    if 'guesses' not in session or 'target_id' not in session:
        return redirect(url_for('index'))

    user_guess = request.form['guess']
    stemmed_guess = stem_word(user_guess)
    previous_guesses = set(guess[0] for guess in session.get('guesses', []))

    print("📥 Raw Guess:", user_guess)
    print("🔎 Stemmed Guess:", stemmed_guess)
    print("🎯 Current Target ID:", session['target_id'])

    if stemmed_guess in previous_guesses:
        session['message'] = "لقد تم تخمين الكلمة من قبل."
    else:
        current_target_id = session['target_id']
        ranking = get_ranking(stemmed_guess, current_target_id)
        print(f"🏆 RANKING RETURNED: {ranking}")  # ✅ ترتيب الكلمة

        if ranking is not None:
            guesses = session.get('guesses', [])
            guesses.append((stemmed_guess, ranking))
            session['guesses'] = guesses
            session['recent_guess'] = stemmed_guess
            session['recent_ranking'] = ranking

            if int(ranking) == 1:
                session['message'] = "تهانينا! لقد ربحت!"
                session['winner'] = True
                print("🏁 PLAYER WON — session['winner'] set ✅")
        else:
            session['message'] = "لم يتم العثور على الكلمة."

    return redirect(url_for('index'))


@app.route('/help_me', methods=['POST'])
def help_me():
    if 'target_id' not in session:
        return redirect(url_for('index'))

    target_id = session['target_id']
    guesses = session.get('guesses', [])

    # استخرج الترتيب الأقرب من المحاولات السابقة (أصغر ترتيب)
    previous_ranks = [rank for _, rank in guesses]
    if previous_ranks:
        nearest_rank = min(previous_ranks)
        suggested_rank = (1 + nearest_rank) // 2
    else:
        suggested_rank = 500  # بداية إذا ما فيه محاولات

    # جلب الكلمة المقابلة لهذا الترتيب من قاعدة البيانات
    conn = sqlite3.connect('semantic_similarity.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.word_text FROM rankings r
        JOIN words w ON r.word_id = w.word_id
        WHERE r.target_id = ? AND r.ranking = ?
    """, (target_id, suggested_rank))
    row = cursor.fetchone()
    conn.close()

    if row:
        word = row[0]
        # نضيفها للمحاولات مباشرة وكأنها تخمين
        guesses.append((word, suggested_rank))
        session['guesses'] = guesses
        session['recent_guess'] = word
        session['recent_ranking'] = suggested_rank

        if suggested_rank == 1:
            session['message'] = "✨ تخمين ممتاز! لقد ربحت!"
            session['winner'] = True
        else:
            session['message'] = f"اقتراح: {word} ← الترتيب: {suggested_rank}"
    else:
        session['message'] = "لم يتم العثور على اقتراح مناسب."

    return redirect(url_for('index'))





@app.route('/delete_word/<int:target_id>', methods=['POST'])
@login_required
def delete_word(target_id):
    try:
        conn = sqlite3.connect('semantic_similarity.db')
        cursor = conn.cursor()

        # Delete related rankings first
        cursor.execute("DELETE FROM rankings WHERE target_id=?", (target_id,))

        # Delete the target word
        cursor.execute("DELETE FROM target WHERE target_id=?", (target_id,))

        # Clean up orphaned words (words that are not linked to any ranking)
        cursor.execute('''
            DELETE FROM words
            WHERE word_id NOT IN (SELECT word_id FROM rankings)
        ''')

        conn.commit()
        conn.close()

        # Reorder IDs and recalculate rankings
        reorder_target_ids()

        return jsonify({"message": "Word deleted successfully.", "status": "success"})
    except Exception as e:
        return jsonify({"message": str(e), "status": "error"})



@app.route('/reset', methods=['POST'])
def reset():
    session.pop('guesses', None)
    session.pop('message', None)
    session.pop('recent_ranking', None)
    session.pop('recent_guess', None)
    session.pop('winner', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.config['SESSION_COOKIE_SAMESITE'] = "None"
    app.config['SESSION_COOKIE_SECURE'] = True
    app.run(host='0.0.0.0', port=5000, debug=True)
