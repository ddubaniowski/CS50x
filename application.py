import os, datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///wheel.db")


@app.route("/")
@login_required
def index():
    """Display wheel of life"""
    colors = ['#ff6961', '#baffc9', '#ffffba', '#cfcfc4', '#bae1ff', '#ffdfba', '#ffd1dc', '#b19cd9']
    labels = ['Kariera', 'Zdrowie', 'Duchowość', 'Emocje', 'Rozrywka', 'Rozwój', 'Relacje', 'Rodzina']

    rows = db.execute("SELECT * FROM wheeldata WHERE id = :user_id", user_id=session["user_id"])

    if rows == []:
        values = [0, 0, 0, 0, 0, 0, 0, 0]
        return render_template('index.html', values=values, colors=colors, labels=labels)

    val_dict = rows[0]
    columns = ["opt1", "opt2", "opt3", "opt4", "opt5", "opt6", "opt7", "opt8"]
    values = []
    for col in columns:
        values.append(val_dict[col])

    return render_template('index.html', values=values, colors=colors, labels=labels)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Proszę podać użytkownika", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Proszę podać hasło", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Nieprawidłowy użytkownik i/lub hasło", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("Witaj! Logowanie udane.")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register new user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        name = request.form.get("username")
        if not name:
            return apology("Proszę podać użytkownika")

        password = request.form.get("password")
        if not password:
            return apology("Proszę podać hasło")

        confirm = request.form.get("confirmation")
        if not password == confirm:
            return apology("Podane hasła nie są zgodne")

        phash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (:name, :phash)", name=name, phash=phash)
        return redirect("/")

    return apology("Rejestracja nie powiodła się - proszę spróbować ponownie")


@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    """Change password"""
    if request.method == "GET":
        return render_template("change.html")

    else:
        password = request.form.get("current")
        if not password:
            return apology("Proszę podać hasło")

        new_password = request.form.get("password")
        if not new_password:
            return apology("Proszę podać nowe hasło")

        confirm = request.form.get("confirmation")
        if not confirm:
            return apology("Proszę powtórzyć nowe hasło")

        if new_password != confirm:
            return apology("Podane hasła nie są zgodne")

        if password == new_password:
            return apology("Nowe hasło nie może być takie same")

        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        user_hash = user[0]["hash"]
        if check_password_hash(user_hash, password):
            phash = generate_password_hash(new_password)
            db.execute("UPDATE users SET hash = :phash WHERE id = :user_id", phash=phash, user_id=session["user_id"])
            return redirect("/")

        return apology("Zmiana hasła nie powiodła się - proszę spróbować ponownie")

@app.route("/wheel", methods=["GET", "POST"])
@login_required
def wheel():
    """Generate wheel of life"""
    if request.method == "GET":
        labels = ['Kariera', 'Zdrowie', 'Duchowość', 'Emocje', 'Rozrywka', 'Rozwój', 'Relacje', 'Rodzina']
        return render_template("wheel.html", labels=labels)
    else:
        opt1 = int(request.form.get("val1"))
        opt2 = int(request.form.get("val2"))
        opt3 = int(request.form.get("val3"))
        opt4 = int(request.form.get("val4"))
        opt5 = int(request.form.get("val5"))
        opt6 = int(request.form.get("val6"))
        opt7 = int(request.form.get("val7"))
        opt8 = int(request.form.get("val8"))
        db.execute("INSERT OR REPLACE INTO wheeldata (id, opt1, opt2, opt3, opt4, opt5, opt6, opt7, opt8) VALUES (:user_id, :opt1, :opt2, :opt3, :opt4, :opt5, :opt6, :opt7, :opt8)",
        user_id=session["user_id"], opt1=opt1, opt2=opt2, opt3=opt3, opt4=opt4, opt5=opt5, opt6=opt6, opt7=opt7, opt8=opt8)
        return redirect("/")

@app.route("/set", methods=["GET", "POST"])
@login_required
def set_goals():
    """Set current goals"""
    if request.method == "GET":
        return render_template("set.html")
    else:
        goal1 = request.form.get("kariera")
        goal2 = request.form.get("zdrowie")
        goal3 = request.form.get("duchowość")
        goal4 = request.form.get("emocje")
        goal5 = request.form.get("rozrywka")
        goal6 = request.form.get("rozwój")
        goal7 = request.form.get("relacje")
        goal8 = request.form.get("rodzina")
        db.execute("INSERT OR REPLACE INTO goaldata (id, goal1, goal2, goal3, goal4, goal5, goal6, goal7, goal8) VALUES (:user_id, :goal1, :goal2, :goal3, :goal4, :goal5, :goal6, :goal7, :goal8)",
        user_id=session["user_id"], goal1=goal1, goal2=goal2, goal3=goal3, goal4=goal4, goal5=goal5, goal6=goal6, goal7=goal7, goal8=goal8)

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        db.execute("INSERT INTO goalhistory (id, goal1, goal2, goal3, goal4, goal5, goal6, goal7, goal8, datetime) VALUES (:user_id, :goal1, :goal2, :goal3, :goal4, :goal5, :goal6, :goal7, :goal8, :timestamp)",
        user_id=session["user_id"], goal1=goal1, goal2=goal2, goal3=goal3, goal4=goal4, goal5=goal5, goal6=goal6, goal7=goal7, goal8=goal8, timestamp=timestamp)

        return redirect("/goals")

@app.route("/goals", methods=["GET"])
@login_required
def goals():
    """Display current goals"""
    labels = ['Kariera', 'Zdrowie', 'Duchowość', 'Emocje', 'Rozrywka', 'Rozwój', 'Relacje', 'Rodzina']

    rows = db.execute("SELECT * FROM goaldata WHERE id = :user_id", user_id=session["user_id"])

    if rows == []:
        goals = ["nie ustawiono", "nie ustawiono", "nie ustawiono", "nie ustawiono", "nie ustawiono", "nie ustawiono", "nie ustawiono", "nie ustawiono"]
        return render_template("goals.html", goals=goals, labels=labels)

    goals_dict = rows[0]

    columns = ["goal1", "goal2", "goal3", "goal4", "goal5", "goal6", "goal7", "goal8"]
    goals = []
    for col in columns:
        goals.append(goals_dict[col])

    return render_template("goals.html", goals=goals, labels=labels)

@app.route("/history", methods=["GET"])
@login_required
def history():
    """Display history of set goals"""

    rows = db.execute("SELECT * FROM goalhistory WHERE id = :user_id ORDER BY datetime DESC", user_id=session["user_id"])
    return render_template("history.html", rows=rows)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)