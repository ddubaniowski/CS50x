import os, datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Display table of user holdings"""
    # assign user_id to variable
    user_id = session["user_id"]

    # query database for user funds
    cash_dict = db.execute("SELECT cash FROM users WHERE id = :user_id",
                                            user_id=user_id)[0]
    cash = cash_dict.get('cash')

    # query database for all stocks held based on transactions
    rows = db.execute("SELECT stock, SUM(number) FROM transactions WHERE id = :user_id GROUP BY stock HAVING SUM(number) > 0 ORDER BY stock",
                                                                                        user_id=user_id)
    # initialise dictionaries and counter
    quotes = {}
    holdings = {}
    total = 0

    # lookup price of each stock held by user and calculate value of total holdings
    for row in rows:
        quote = lookup(row["stock"])["price"]
        number = row["SUM(number)"]
        quotes[row["stock"]] = quote
        holdings[row["stock"]] = number
        total = total + (quote * number)

    # render index template and pass required parameters
    return render_template("index.html", rows=rows, quotes=quotes, holdings=holdings, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # return buy template if user requests page
    if request.method == "GET":
        return render_template("buy.html")

    # if user submits to page
    else:
        # assign stock name to variable and return apology if field empty
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Must provide stock name")

         # assign number of shares to variable and return apology if not positive integer
        number = int(request.form.get("shares"))
        if number < 0:
            return apology("Number of shares must be positive")

        quote = lookup(symbol)
        price = quote["price"]
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        cash_dict = db.execute("SELECT cash FROM users WHERE id = :user_id",
                                            user_id=session["user_id"])[0]
        cash = cash_dict.get('cash')

        if (price * number) > cash:
            return apology("You don't have enough funds to make this purchase.")

        db.execute("INSERT INTO transactions (id, stock, price, number, datetime) VALUES (:user_id, :stock, :price, :number, :datetime)",
                                                    user_id=session["user_id"], stock=symbol, price=price, number=number, datetime=timestamp)
        # cash = float(cash)
        cash = cash - (price * number)
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash=cash, user_id=session["user_id"])

        return redirect("/")

    return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT stock, price, number, datetime FROM transactions WHERE id = :user_id ORDER BY datetime DESC",
                                                                                        user_id=session["user_id"])
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        quote = lookup(request.form.get("symbol"))
        if not quote:
            return apology("Unable to find " + request.form.get("symbol"))
        return render_template("quoted.html", quote=quote)
    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    else:
        name = request.form.get("username")
        if not name:
            return apology("You must provide a username")

        password = request.form.get("password")
        if not password:
            return apology("You must provide a password")

        confirm = request.form.get("confirmation")
        if not password == confirm:
            return apology("The provided passwords do not match")

        phash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (:name, :phash)", name=name, phash=phash)
        return redirect("/")

    return apology("Registration failed - please try again")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # query database for all stocks held based on transactions
    rows = db.execute("SELECT stock, SUM(number) FROM transactions WHERE id = :user_id GROUP BY stock ORDER BY stock", user_id=session["user_id"])

    if request.method == "GET":
        return render_template("sell.html", rows=rows)

    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Please select stock to sell")

        number = request.form.get("shares")
        if not number:
            return apology("Please enter number of shares to sell")

        number = int(number)
        if number < 1:
            return apology("Number of shares must be positive")

        stock = next(item for item in rows if item["stock"] == symbol)
        if stock["SUM(number)"] < number:
            return apology("You don't have that many shares of " + symbol)

        cash_dict = db.execute("SELECT cash FROM users WHERE id = :user_id",
                                            user_id=session["user_id"])[0]
        cash = cash_dict.get('cash')

        price = lookup(symbol)["price"]
        value = number * price
        cash += value
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash=cash, user_id=session["user_id"])

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        number *= -1
        db.execute("INSERT INTO transactions (id, stock, price, number, datetime) VALUES (:user_id, :stock, :price, :number, :datetime)",
                                                user_id=session["user_id"], stock=symbol, price=price, number=number, datetime=timestamp)

        return redirect("/")

@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    """Change passowrd"""
    if request.method == "GET":
        return render_template("change.html")

    else:
        password = request.form.get("current")
        if not password:
            return apology("Please enter current password")

        new_password = request.form.get("password")
        if not new_password:
            return apology("Please enter new password")

        confirm = request.form.get("confirmation")
        if not confirm:
            return apology("Please confirm new password")

        if new_password != confirm:
            return apology("Passwords do not match")

        if password == new_password:
            return apology("New password cannot be the same as old")

        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        user_hash = user[0]["hash"]
        if check_password_hash(user_hash, password):
            phash = generate_password_hash(new_password)
            db.execute("UPDATE users SET hash = :phash WHERE id = :user_id", phash=phash, user_id=session["user_id"])
            return redirect("/")

        return apology("Password change failed")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
