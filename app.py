# import requirements
from flask import Flask, redirect, render_template, request, session, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import sqlite3

# Configure Application
app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

# Configure Session
app.config["SESSION_PERMANENT"] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Connect to database
conn = sqlite3.connect('codepartner.db', check_same_thread=False)
cursor = conn.cursor()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # Register User

    user_email = request.form.get("email")
    username = request.form.get("username")
    user_password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    # Check if method is POST
    if request.method == "POST":
        # Check if the user filled the form
        if not user_email:
            return("No email")
        elif not username:
            return("No username")
        elif not user_password:
            return("No password")
        elif user_password != confirmation:
            return("Passwords do not match")
        
        # Generate password hash for the user
        password_hash = generate_password_hash(user_password)

        # Check if user exists and insert into database
        cursor.execute("SELECT username, email FROM users WHERE username = ? or email = ?", (username, user_email))
        existing_data = cursor.fetchall()
        if existing_data:
            return ("Username or email is already taken.")
        else:
            cursor.execute("INSERT INTO users (email, username, password_hash, registration_date) VALUES (?, ?, ?, ?)",(user_email, username, password_hash, date.today()))
            conn.commit()

        # Send an alert if successful
        flash("Account successfully created!")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Log user in
    session.clear()

    if request.method == "POST":

        # Ensure information submitted
        if not request.form.get("username"):
            return ("No username")
        elif not request.form.get("password"):
            return ("no password")
        
        # Check database for username
        cursor.execute("SELECT * FROM users WHERE username = ?", [request.form.get("username")])
        rows = cursor.fetchall()

        # Ensure that user exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][3], request.form.get("password")):
            return ("Wrong username or password!")
        
        # Remeber Session information
        session["user_id"] = rows[0][0]
        session["username"] = request.form.get("username")    

        # Redirect to homepage
        return redirect("/")

        


    return render_template("login.html")

