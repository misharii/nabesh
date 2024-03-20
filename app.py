# app.py
from flask import Flask, request, render_template, session, url_for, redirect
from flask_session import Session  # Ensure Flask-Session is installed and imported if you're using it
from compute import SemanticSimilarity


app = Flask(__name__)


# Configure your Flask app for session use, e.g., secret key and optionally Flask-Session settings
app.config['SECRET_KEY'] = '123'
app.config['SESSION_PERMANENT'] = False

#need to store session in database in production insted of filesystem
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


similarity_computer = SemanticSimilarity()


# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if 'guesses' not in session:
#         session['guesses'] = []  # Initialize 'guesses' in the session if not already present
#
#     message = None
#     if request.method == 'POST':
#         if request.form.get('action') == 'reset':  # Check if the reset action was triggered
#             print("Resetting guesses")  # Debug print
#             session.pop('guesses', None)
#             return redirect(url_for('index'))  # Redirect to clear form data and prevent resubmission
#
#         user_guess = request.form['guess']
#         stemmed_guess = similarity_computer.stem_word(user_guess)  # Assuming this method exists and works
#         previous_guesses = [guess[0] for guess in session.get('guesses', [])]
#         print(previous_guesses)
#
#         if stemmed_guess in previous_guesses:
#             message = "Word has been guessed before."
#         else:
#             ranking = similarity_computer.get_ranking(stemmed_guess)  # Get ranking for the stemmed guess
#             if ranking is not None:
#                 # message = f"The stemmed form '{stemmed_guess}' (from your input '{user_guess}') is ranked at position {ranking}."
#                 session['guesses'].append((user_guess, ranking))  # Append the original guess and its ranking
#                 session.modified = True  # Mark the session as modified to ensure it gets saved
#             else:
#                 message = "Word not found in precomputed rankings."
#
#     # Sort guesses by ranking
#     sorted_guesses = sorted(session['guesses'], key=lambda x: x[1])
#
#     return render_template('index.html', message=message, guesses=sorted_guesses)

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
        return redirect(url_for('index'))
    else:
        ranking = similarity_computer.get_ranking(stemmed_guess)
        if ranking is not None:
            session['guesses'].append((stemmed_guess, ranking))
            # No need to explicitly mark the session as modified for simple operations
        else:
            # Redirect with a message if the word is not found
            session['message'] = "لم يتم العثور على الكلمة."
            return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/reset', methods=['POST'])
def reset():
    # Clear the guesses from the session
    session.pop('guesses', None)
    return redirect(url_for('index'))





if __name__ == '__main__':
    app.run(debug=True)
