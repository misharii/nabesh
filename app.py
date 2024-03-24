# ngrok http http://localhost:5000

# app.py
from flask import Flask, request, render_template, session, url_for, redirect
from flask_session import Session  # Ensure Flask-Session is installed and imported if you're using it
from compute import SemanticSimilarity


app = Flask(__name__)


# Configure your Flask app for session use, e.g., secret key and optionally Flask-Session settings
app.config['SECRET_KEY'] = '123'
app.config['SESSION_PERMANENT'] = True

#need to store session in database in production insted of filesystem

# app.config['SESSION_TYPE'] = 'filesystem'
# Session(app)


similarity_computer = SemanticSimilarity()


@app.route('/', methods=['GET'])
def index():
    # Display the main page with guesses or an empty list

    # semantic_similarity = SemanticSimilarity()
    # top_rankings = semantic_similarity.get_top_rankings()
    # print(top_rankings)

    guesses = session.get('guesses', [])
    sorted_guesses = sorted(guesses, key=lambda x: x[1])
    message = session.pop('message', None) if 'message' in session else None
    return render_template('index.html', guesses=sorted_guesses, message=message)



# WORKING FINE

@app.route('/guess', methods=['POST'])
def guess():
    # Ensure 'guesses' key exists in session
    if 'guesses' not in session:
        session['guesses'] = []

    user_guess = request.form['guess']
    stemmed_guess = similarity_computer.stem_word(user_guess)
    previous_guesses = set(guess[0] for guess in session.get('guesses', []))

    if stemmed_guess in previous_guesses:
        session['message'] = "لقد تم تخمين الكلمة من قبل."
    else:
        ranking = similarity_computer.get_ranking(stemmed_guess)
        if ranking is not None:
            session['guesses'].append((stemmed_guess, ranking))
            # Store the most recent guess and its ranking separately
            session['recent_guess'] = stemmed_guess
            session['recent_ranking'] = ranking
        else:
            session['message'] = "لم يتم العثور على الكلمة."

    return redirect(url_for('index'))



@app.route('/reset', methods=['POST'])
def reset():
    session.pop('guesses', None)
    session['message'] = ''
    return redirect(url_for('index'))





if __name__ == '__main__':
    app.run(debug=True)
