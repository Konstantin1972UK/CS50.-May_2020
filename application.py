import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

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


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id_user = session["user_id"]
    current_user_info = db.execute("SELECT * FROM data_user_id{}".format(id_user))
    user_cash = db.execute("SELECT cash FROM users WHERE id = '{}' ".format(id_user))
    user_cash = usd(user_cash[0]['cash'])
    
    l_symbol = sorted(set([i['Symbol'] for i in current_user_info]))
    l_res = []
    user_shares = 0
    for i in l_symbol:
        user_symbol = db.execute("SELECT * FROM data_user_id{} WHERE Symbol = '{}' ".format(id_user, i))
        total = sum([int(i['Share'])*i['Price'] for i in user_symbol])
        share = sum([int(i['Share']) for i in user_symbol])
        price = 0 if share == 0 else total/share
        name = user_symbol[0]['Name']
        l_res.append({'name': name, 'share': share, 'symbol': i, 'total': usd(total), 'price': usd(price)})
        user_shares += total
    
    
    l_res = [i for i in l_res if i['share'] != 0]
    return render_template("index.html",user_cash=user_cash, items=l_res, user_shares=usd(user_shares))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        
        if not symbol:
                return apology("must provide SYMBOL")
        if not shares:
                return apology("must provide SHARES")
        try:
           shares = int(shares)
        except:
            return apology("must be INTEGER")
        if shares <= 0:
            return apology("must be INTEGER > 0")
        res =  lookup(symbol)
        print('res = ', res, res == None)
        if res == None:
            return apology("must be WRONG NAMEL")

        current_user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        current_user = current_user[0]

        current_user_cash = current_user['cash']

        price = round(res['price'], 2)
        
        name = res['name']

        possible = int(current_user_cash//price)

        if price*int(shares) >= current_user_cash:
            return apology("nYou can buy only {} shares".format(possible))

        date_time = datetime.now()
        t = date_time.strftime("%Y-%m-%d %H:%M:%S")

        money_all = current_user["cash"]
        money_new = money_all - price*int(shares)
        print('money_all = ', money_all)
        print('price*int(shares) = ', price*int(shares))
        print('money_new = ', money_new)
        id_user = session["user_id"]
        
        db.execute("UPDATE users SET cash =:cash WHERE id =:id", cash=money_new, id=session["user_id"])
        
        db.execute("INSERT INTO :table (Symbol, Name, Share, Price, Transcated)\
        VALUES (:Symbol, :Name, :Share, :Price, :Transcated)",\
        table='data_user_id{}'.format(id_user),\
        Symbol=symbol, Name=name, Share=shares, Price=price, Transcated=t)
        messege = 'You bought {} {} at {} per stock which is worth {}\
        You now have {} left to spend'.format(symbol, shares, usd(price), usd(price*int(shares)), usd(money_new))
        flash('Bought! \n{}'.format(messege))
        return redirect("/")
     
@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    name = request.args.get("username")
    print('name =', name)
    if not name:
        return jsonify(False)
    candidat = db.execute("SELECT * FROM users WHERE username = :username", username = name)
    return jsonify(False if candidat else True)

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    id_user = session["user_id"]
    current_user_info = db.execute("SELECT * FROM data_user_id{}".format(id_user))

    return render_template("history.html", items=current_user_info)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":    
        # Ensure username was submitted
        if not name:
            return apology("must provide username")
        if request.method == "POST":
            name     = request.form.get("username")
            password = request.form.get("password")

        # Ensure password was submitted
        elif not password:
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=name)

        if len(rows) != 1:
            return apology("invalid username")

        password = request.form.get("password")

        if  not check_password_hash(rows[0]['hash'], password):
              return apology("invalid pasword  testing")

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
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        res = lookup(symbol)

        if not res:
            return apology("WRONG Symbol")
        text = 'A share of {} ({}) costs ${:.2f}.'.format(res['name'], res['symbol'], res['price'])
        return render_template("quoted.html", text=text)

@app.route("/register", methods=["GET","POST"])
def register():
    # Forget any user_id
    session.clear()
    username     = request.form.get("username")
    password     = request.form.get("password")
    confirmation = request.form.get("confirmation")

    if request.method == "POST":
        if not username or not password  or not confirmation:
            return apology("try to fill ALL fields")

        if password != confirmation:
            return apology("passwords don't match")

        id_new = db.execute("SELECT * FROM users WHERE username = :username", username = username)

        if len(id_new) != 0:
            return apology("name is not UNIC", 400)

        hash_pwd = generate_password_hash(password)

        id_user = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=hash_pwd)

        name_table = "data_user_id{}".format(id_user)

        db.execute("CREATE TABLE :name_table ('id'  integer PRIMARY KEY NOT NULL, 'Symbol' TEXT NOT NULL ,\
            'Name'  TEXT NOT NULL, 'Share' TEXT NOT NULL, 'Price'  numeric(2) NOT NULL, 'Transcated' datetime NOT NULL)",\
            name_table=name_table)

        session["user_id"] = id_user
        flash("Registred!")

        return redirect ("/")
        # return render_template ("blank.html")


  #User reached route via GET
    else:
        return render_template("register.html")

@app.route("/sell", methods=["POST", "GET"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        id_user = session["user_id"]
        current_user_info = db.execute("SELECT * FROM data_user_id{}".format(id_user))
        l_symbol = sorted(set([i['Symbol'] for i in current_user_info]))

        return render_template("sell.html", items=l_symbol)
    else:
        id_user = session["user_id"]
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
                return apology("must provide SYMBOL")
        elif not shares:
                return apology("must provide SHARES")

        res =  lookup(symbol)

        if res == None:
            return apology("no SYMBOL in trade")

        current_user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        current_user = current_user[0]
        current_user_cash = current_user['cash']

        price = round(res['price'],2)
        name  = res['name']

        user_symbol = db.execute("SELECT * FROM data_user_id{} WHERE Symbol = '{}' ".format(id_user, symbol))

        shares_quantity = sum([int(i['Share']) for i in user_symbol])

        if shares_quantity < int(shares):
            return apology("You can only sell {} shares".format(shares_quantity))

        date_time = datetime.now()
        t = date_time.strftime("%Y-%m-%d %H:%M:%S")

        money_new = current_user_cash + int(shares) * price
        new_shares = - int(shares)

        db.execute("UPDATE users SET cash =:cash WHERE id =:id", cash=money_new, id=session["user_id"] )
        db.execute("INSERT INTO :table (Symbol, Name, Share, Price, Transcated)\
        VALUES (:Symbol, :Name, :Share, :Price, :Transcated)",\
        table='data_user_id{}'.format(id_user),\
        Symbol=symbol, Name=name, Share=new_shares, Price=price, Transcated=t)
        messege = 'You SOLD {} {} at {} per stock which is worth {}\
        You now have {} left to spend'.format(shares, symbol,  usd(price), usd(price*int(shares)), usd(money_new))
        flash('{}'.format(messege))
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

