import os, json
from static import *
from flask import Flask, session, render_template, url_for, flash, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from flask_login import LoginManager
import requests
from helpers import login_required
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

app = Flask(__name__)
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
#app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()
    username = request.form.get("username")

    if request.method == "POST":

        if not request.form.get("username"):
            return render_template("error.html", message="Enter user")

        elif not request.form.get("password"):
            return render_template("error.html", message="Enter password")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username": username})
        
        result = rows.fetchone()

        if result == None or not check_password_hash(result[2], request.form.get("password")):
            return render_template("error.html", message="invalid username or password")

        session["user_id"] = result[0]
        session["user_username"] = result[1]

        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/loginRegister", methods=["GET", "POST"])
def loginRegister():

    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return render_template("error.html", message="Enter user")

        userCheck = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":request.form.get("username")}).fetchone()

        if userCheck:
            return render_template("error.html", message="User exists")

        elif not request.form.get("password"):
            return render_template("error.html", message="Enter password")

        elif not request.form.get("confirmation"):
            return render_template("error.html", message="Confirm password")

        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message="passwords do not match")
        
        hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
        
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                            {"username":request.form.get("username"), 
                             "password":hashedPassword})

        db.commit()

        return redirect("/login")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
  
    session.clear()
    return redirect("/")

@app.route("/search", methods=["GET","POST"])
@login_required
def search():

    if not request.args.get("book"):
        return render_template("error.html", message="you must provide a book.")

    query = "%" + request.args.get("book") + "%"

    query = query.title()
    
    rows = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn LIKE :query OR \
                        title LIKE :query OR \
                        author LIKE :query LIMIT 10",
                        {"query": query})

    if rows.rowcount == 0:
        return render_template("error.html", message="we can't find books with that description.")

    books = rows.fetchall()
    return render_template("results.html", books=books)

@app.route("/book/<isbn>", methods=['GET','POST'])
@login_required
def book(isbn):

    if request.method == 'POST':

        currentUser = session["user_id"]

        revw = request.form.get("review")

        rating = request.form.get("rating")

        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
            {"isbn": isbn})

        bookId = row.fetchone() 
        bookId = bookId[0]

        row2 = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                    {"user_id": currentUser,
                     "book_id": bookId})

        if row2.rowcount == 1:
            
            return render_template("error.html", message = "You alredy submit a review to this book")

        rating = int(rating)

        db.execute("INSERT INTO reviews (user_id, book_id, review, rating) VALUES (:user_id, :book_id, :review, :rating)",
                    {"user_id": currentUser, 
                    "book_id": bookId, 
                    "review": revw, 
                    "rating": rating})

        db.commit()
        
        return redirect("/book/" + isbn)

    else:

         row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})
                        
    bookInfo = row.fetchall()

    key = os.getenv("GOODREADS_KEY")

    query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})

    response = query.json()
    response = response['books'][0]     
    bookInfo.append(response)  

    row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

    book = row.fetchone()
    book = book[0]
    
    results = db.execute("SELECT users.username, review, rating FROM users INNER JOIN reviews ON users.id = reviews.user_id WHERE book_id = :book",
                            {"book": book})         

    reviews = results.fetchall()

    return render_template("book.html", bookInfo=bookInfo, reviews=reviews)

@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api(isbn):
    
    row = db.execute("SELECT title, author, year, isbn, \
                    COUNT(reviews.id) as review_count, \
                    AVG(reviews.rating) as average_score \
                    FROM books \
                    INNER JOIN reviews \
                    ON books.id = reviews.book_id \
                    WHERE isbn = :isbn \
                    GROUP BY title, author, year, isbn",
                    {"isbn": isbn})

    if row.rowcount != 1:
        return render_template("error.html", message="This book dont have reviews")
  
    tmp = row.fetchone()

    result = dict(tmp.items())

    result['average_score'] = float('%.2f'%(result['average_score']))

    return jsonify(result) 



        