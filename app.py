# import requirements
from flask import Flask, redirect, render_template, request, session, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
import sqlite3
import re

# Configure Application
app = Flask(__name__)

# Configure Session
app.config["SESSION_PERMANENT"] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Regular expressions for username and password validation
username_regex = r'^[a-zA-Z0-9_-]{3,20}$'
password_regex = r'^.{6,}$'

# Connect to database
conn = sqlite3.connect('codepartner.db', check_same_thread=False)
cursor = conn.cursor()

@app.route("/register", methods=["GET", "POST"])
def register():
    # Register User

    if session.get("user_id") is None:

        user_email = request.form.get("email")
        username = request.form.get("username")
        user_password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # Check if method is POST
        if request.method == "POST":
            # Check if the user filled the form
            if not user_email or not username or not user_password or user_password != confirmation:
                flash("An error occurred while processing your registration.", 'error')
                return render_template("register.html")
            
            # Check if form meets regex
            if not re.match(username_regex, username) or not re.match(password_regex, user_password):
                return("Not a valid username or password") 
            
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
            flash("Welcome aboard! Your account has been created.")

    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Log user in
    session.clear()

    if session.get("user_id") is None:

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
            session['logged_in'] = True  

            # Redirect to homepage
            return redirect("/partner")      

    return redirect("index")

@app.route("/logout")
def logout():
    # Forget any user_id
    session['logged_in'] = False  

    session.clear()
    # Redirect user to login form
    return redirect("/")

@app.route("/")
def index():
    if session.get("user_id") is None:
        return render_template("/index.html")
    else:
        return redirect("partner")
    
@app.route("/partner", methods=["GET", "POST"])
def partner():
    # Check if user is logged in
    if session.get("user_id") is None:
        return ("You are not logged in")
    
    # If user is logged in check if method is POST
    if request.method == "POST":
            # If method is post ensure the form submitted correctly
            category = request.form.get("category")
            subject = request.form.get("subject")

            if not subject:
                flash("No Subject!", 'error')
                return redirect("partner")
            
            # If category submitted correctly find category ID
            if not category:
                flash("No Category Selected!", 'error')
                return redirect("partner")
            else:
                cursor.execute("SELECT id FROM categories WHERE category_name = ?", [category])
                category_id = cursor.fetchall()[0][0]

            # Submit the post to database
            cursor.execute("INSERT INTO posts (content, user_id, category_id, creation_date, last_modified) VALUES (?, ?, ?, ?, ?)", (subject, int(session["user_id"]), int(category_id), date.today(), datetime.now()))
            conn.commit()

            return redirect("partner")

    if request.method == "GET":    
        page = request.args.get('page', 1, type=int)

        # Calculate the offset based on the page and per_page values
        offset = (page - 1) * 10
        
        # Query the database to get the posts for the current page in descending order
        cursor.execute("""SELECT posts.id, posts.content, posts.creation_date, users.username, categories.category_name 
                    FROM posts
                    JOIN users ON users.id = posts.user_id 
                    JOIN categories ON categories.id = posts.category_id
                    ORDER BY posts.last_modified DESC
                    LIMIT ? OFFSET ?;""", (10, offset))
        posts = cursor.fetchall()
        print(posts)

        # Query the database to get the total count of posts
        cursor.execute("SELECT COUNT(*) FROM posts;")
        total_posts = cursor.fetchall()[0][0]

        total_pages = (total_posts + 10 - 1) // 10

        # Select all category names from database
        cursor.execute("SELECT category_name FROM categories")
        rows = cursor.fetchall()
        
        # Send all posts to partner page
        return render_template("partner.html", posts = posts , total_pages = total_pages, page = page, cats=rows)

@app.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    # Check if method is POST
    if request.method == "POST":
        # Add reply to the database
        cursor.execute("INSERT INTO replies (post_id, user_id, content, creation_date) VALUES (?, ?, ?, ?)", (id, int(session["user_id"]), request.form.get("reply"), date.today()))
        conn.commit()

    # Query database to get the post information
    cursor.execute("""SELECT posts.content, posts.creation_date, users.username, categories.category_name
                   FROM posts
                   JOIN users ON users.id = posts.user_id 
                   JOIN categories ON categories.id = posts.category_id
                   WHERE posts.id = ?;""", [int(id)])
    post = cursor.fetchall()
    print(post)

    # Query database to get replies
    cursor.execute("""SELECT replies.content, replies.creation_date, users.username
                   FROM replies
                   JOIN users ON users.id = replies.user_id
                   WHERE post_id = ?""", [int(id)])
    replies = cursor.fetchall()
    return render_template("post.html", post=post, id = id, replies = replies)
    
@app.route("/profile")
def profile():
    # Query database to get the profule information and display it in the profile page
    cursor.execute("SELECT email, username, first_name, last_name, birth_date, registration_date FROM users WHERE id = ?", [session['user_id']])
    rows = cursor.fetchall()
    return render_template("profile.html", rows = rows)

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    # Query database to get the profile information to display it in the editing fields
    cursor.execute("SELECT email, username, first_name, last_name, birth_date, registration_date FROM users WHERE id = ?", [session['user_id']])
    rows = cursor.fetchall()

    user_email = rows[0][0]
    first_name = rows[0][2]
    last_name = rows[0][3]
    birthday = rows[0][4]

    # Check if method is POST
    if request.method == "POST":
        # Check if values in the form have changed
        if request.form.get("email") != rows[0][0]:
            user_email = request.form.get("email")

        if request.form.get("first_name") != rows[0][2]:
            first_name = request.form.get("first_name")

        if request.form.get("last_name") != rows[0][3]:
            last_name = request.form.get("last_name")

        if request.form.get("birthday") != rows[0][4]:
            birthday = request.form.get("birthday")

        cursor.execute("""UPDATE users
                       SET email = ?,
                        first_name = ?,
                        last_name = ?,
                        birth_date = ?
                        WHERE id = ?""",
                        (user_email, first_name, last_name, birthday, session["user_id"]))
        
        return redirect("profile")
        
    return render_template("edit_profile.html", rows = rows)

@app.route("/password_change", methods=["GET", "POST"])
def password_change():
    # Change password feature

    #Check if method is POST
    if request.method == "POST":
        # Ensure previous password was submitted
        if not request.form.get("prev-pswd"):
            flash("Type in your current password!")
            return render_template("password_change.html")

        # Ensure new password was submitted
        if not request.form.get("new-pswd"):
            flash("Type in your new password!")
            return render_template("password_change.html")
        
        # Select user hashed_password from db
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", [session['user_id']])
        rows = cursor.fetchall()[0][0]

        # Check if form previous password is equal with current hash
        if not check_password_hash(rows, request.form.get("prev-pswd")):
            flash("Previous password is not correct!")
            return render_template("password_change.html")

        # Check if repeat password is correct
        if not request.form.get("new-pswd") == request.form.get("rpt-pswd"):
            flash("New password doesn't match!")
            return render_template("password_change.html")

        new_pswd_hash = generate_password_hash(request.form.get("new-pswd"))
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_pswd_hash, session["user_id"]))

        flash('Password succesfuly changed!')
        

    return render_template("password_change.html")