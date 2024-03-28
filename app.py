# ngrok http http://localhost:5000
# flask run --host=0.0.0.0 --port=5000

# app.py
from flask import Flask, request, render_template, session, redirect, url_for, flash
from functools import wraps
# from flask_session import Session
from precompute import *
import sqlite3
from datetime import datetime



app = Flask(__name__)


# Configure your Flask app for session use, e.g., secret key and optionally Flask-Session settings
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in
    if 'user_id' in session:
        return redirect(url_for('adminPanel'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        createDB()
        conn = sqlite3.connect('semantic_similarity.db')
        cursor = conn.cursor()

        # Fetch the admin user from the database
        cursor.execute("SELECT * FROM admins WHERE username=? AND password=?", (username, password))
        admin = cursor.fetchone()
        # Close the database connection
        conn.close()
        # Check if the admin exists and the password matches
        if admin:
            session['user_id'] = admin[0]  # Assuming the user_id is the first column
            session['username'] = username
            session['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Redirect to the admin panel or 'next' if safe to do so
            next_page = request.args.get('next') or url_for('adminPanel')
            return redirect(next_page)
        else:
            # Flash a message if login fails
            flash('Login failed. Please check your username and password.', 'warning')

    # Render the login page
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Removing user_id from session
    return redirect(url_for('login'))


@app.route('/adminPanel', methods=['GET', 'POST'])
@login_required
def adminPanel():
    all_target_words = get_all_target_words()
    if request.method == 'POST':
        word_count = int(request.form.get('wordCount', 0))
        target_words_list = [request.form.get(f'word{i}') for i in range(word_count) if request.form.get(f'word{i}')]
        if not target_words_list:
            flash('No words entered. Please add words before submitting.', 'danger')
            return redirect(url_for('adminPanel'))

        stemmed_target_words = stem_words(target_words_list)
        word_list = wordlistOpentxt()
        try:
            model_load_time, computation_time = precompute_rankings(stemmed_target_words, word_list)
            return render_template('adminPanel.html', model_load_time=model_load_time,
                                   computation_time=computation_time, all_target_words=all_target_words)

        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')

    return render_template('adminPanel.html', all_target_words=all_target_words)

@app.route('/', methods=['GET'])
def index():

    conn = sqlite3.connect('semantic_similarity.db')
    cursor = conn.cursor()
    # games are fetched in ascending order by target_id
    cursor.execute('SELECT target_id, target_text FROM target ORDER BY target_id ASC')
    games = cursor.fetchall()
    conn.close()

    guesses = session.get('guesses', [])
    sorted_guesses = sorted(guesses, key=lambda x: x[1])
    message = session.pop('message', None) if 'message' in session else None
    return render_template('index.html', guesses=sorted_guesses, message=message, games=games)


@app.route('/guess', methods=['POST'])
def guess():
    if 'guesses' not in session or 'target_id' not in session:
        # Redirect to a page to select a target word if not set
        return redirect(url_for('index'))

    user_guess = request.form['guess']
    stemmed_guess = stem_word(user_guess)
    previous_guesses = set(guess[0] for guess in session['guesses'])


    if stemmed_guess in previous_guesses:
        session['message'] = "لقد تم تخمين الكلمة من قبل."
    else:
        # Use the stored target_id for the current game session
        current_target_id = session['target_id']
        ranking = get_ranking(stemmed_guess, current_target_id)
        if ranking is not None:
            session['guesses'].append((stemmed_guess, ranking))
            session['recent_guess'] = stemmed_guess
            session['recent_ranking'] = ranking
        else:
            session['message'] = "لم يتم العثور على الكلمة."

    return redirect(url_for('index'))

@app.route('/start/<int:target_id>', methods=['GET'])
def start_game(target_id):
    # Start a new game with the selected target word
    session['target_id'] = target_id
    session['guesses'] = []  # Reset guesses for the new game
    session['recent_ranking'] = ""
    return redirect(url_for('index'))


@app.route('/reset', methods=['POST'])
def reset():
    session.pop('guesses', None)
    session['message'] = ''
    session['recent_ranking'] = ""
    return redirect(url_for('index'))





if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='192.168.10.111', port=5000, debug=True)

