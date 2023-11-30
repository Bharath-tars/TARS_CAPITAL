import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT * FROM portfolio where user_id = ?",session["user_id"])
    cash = db.execute("SELECT cash from users where id=?",session["user_id"])[0]["cash"]
    total = db.execute(
        "SELECT SUM(shares * price) FROM portfolio WHERE user_id = ?", session["user_id"])[0]["SUM(shares * price)"]
    if total == None:
        total = 0
    return render_template("index.html", rows=rows, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if symbol == None:
            return apology("invalid symbol", 400)

        try:
            data = lookup(symbol)
            price = data["price"]
            total_cost = int(price) * int(shares)
            print(total_cost)
            cash = db.execute("SELECT cash from users where id=?",session["user_id"])[0]["cash"]
        except:
            return apology("invalid symbol", 400)

        if not request.form.get("shares").isdigit():
            return apology("invalid number of shares", 400)
        elif int(request.form.get("shares")) <= 0:
            return apology("invalid number of shares", 400)
        elif total_cost > cash:
            return apology("Insufficient Money to Purchase.. Meoww",400)
        else:
            db.execute("INSERT INTO history(user_id,name,symbol,price,shares) values (?, ?, ?, -?, +?)",session["user_id"],data["name"],data["symbol"],price,shares)
            row = db.execute("SELECT * FROM portfolio where symbol = ? AND user_id = ?",symbol, session["user_id"])

            if len(row)==1:
                db.execute("UPDATE portfolio SET shares = shares + ? WHERE user_id = ? AND symbol = ?",
                           shares, session["user_id"], symbol)
            else:
                db.execute("INSERT INTO portfolio (user_id, symbol, name, shares, price) VALUES(?, ?, ?, ?, ?)",
                           session["user_id"], symbol, data["name"], shares, price)
            db.execute("UPDATE users SET cash = cash - ? WHERE id = ?",
                       price * int(shares), session["user_id"])

            return redirect("/",)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    portfolio_history = db.execute("SELECT name, shares, price, transaction_at from history where user_id = ?",session["user_id"])
    return render_template("history.html", portfolio_history = portfolio_history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if symbol == None:
            return apology("invalid symbol", 400)
        try:
            result = lookup(symbol)
            if result is not None:
                name = result["name"]
                symbol = result["symbol"]
                price = result["price"]
                return render_template("quoted.html", name=name, symbol=symbol, price=price)
            else:
                return apology("invalid symbol", 400)
        except:
            return apology("must provide a valid symbol", 403)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide a password", 403)

        elif not request.form.get("newpassword"):
            return apology("Both the entered passwords aren't correct", 403)

        username = request.form.get("username")
        password = request.form.get("password")
        new_password = request.form.get("newpassword")
        if password != new_password:
            return apology("Incorrect Re-entry Password", 403)
        new_pass = generate_password_hash(password)
        db.execute("INSERT INTO users(username, hash) values (?, ?)",username,new_pass)
        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    symbols= db.execute("SELECT symbol FROM portfolio WHERE user_id = ?",session["user_id"])
    if request.method=="POST":
        symbol = request.form.get("sharesymbol")
        shares = request.form.get("shares")
        if symbol == None:
            return apology("No symbol, Sell u MF", 400)
        data = lookup(symbol)
        price = data["price"]
        shares_present = db.execute("SELECT shares from portfolio where user_id = ?  AND symbol = ?",session["user_id"],symbol)[0]["shares"]
        if not request.form.get("shares").isdigit():
            return apology("invalid number of shares", 400)
        elif int(request.form.get("shares")) <= 0:
            return apology("invalid number of shares", 400)
        elif int(shares) > int(shares_present):
            return apology("Insufficient shares to sell.. Meoww",400)
        else:
            db.execute("INSERT into history(user_id,name,symbol,price,shares) values(?, ?, ?, +?, -?)",session["user_id"],data["name"],symbol,price,shares)
            rows = db.execute("SELECT * from portfolio where symbol = ? and user_id = ?",symbol,session["user_id"])
            if len(rows)==1:
                db.execute("UPDATE portfolio SET shares = shares - ? where user_id = ? and symbol = ?",shares,session["user_id"],symbol)

            db.execute("DELETE FROM portfolio WHERE shares = 0 AND user_id = ? AND symbol = ?",session["user_id"], symbol)
            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?",price * int(shares), session["user_id"])
            return redirect("/")
    return render_template("sell.html", symbols=symbols)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        amt = request.form.get("amt")
        if not request.form.get("amt").isdigit():
            return apology("invalid amount", 400)
        elif int(request.form.get("amt")) <= 0:
            return apology("invalid amount", 400)
        elif int(amt) > 10000:
            return apology("Can only request $10,000.00 at a time!",400)
        db.execute("UPDATE users SET cash = cash + ? where id = ?",int(amt),session["user_id"])
        return redirect("/")
    else:
        return render_template("add.html")

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    cash = db.execute("SELECT cash from users  where id = ?", session["user_id"])[0]["cash"]
    if request.method == "POST":
        amt = request.form.get("amt")
        if cash < 0:
            return apology("You still owe me $$ MF", 400)
        if not request.form.get("amt").isdigit():
            return apology("invalid amount", 400)
        elif int(request.form.get("amt")) <= 0:
            return apology("invalid amount", 400)
        elif int(amt) > cash:
            return apology("Withdraw when you have enough money!",400)
        db.execute("UPDATE users SET cash = cash - ? where id = ?",int(amt),session["user_id"])
        return redirect("/")
    else:
        return render_template("withdraw.html")
