# import requirements
from flask import Flask, redirect, render_template, request, session, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import sqlite3

# Configure Application
app = Flask(__name__)

# Configure Session
app.config["SESSION_PERMANENT"] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Connect to database
conn = sqlite3.connect('codepartner.db', check_same_thread=False)
cursor = conn.cursor()

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
        session['logged_in'] = True  

        # Redirect to homepage
        return redirect("/")      

    return render_template("login.html")

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
        return render_template("index.html")
    else:
        return render_template("index.html")
    
@app.route("/partner")
def partner():
    page = request.args.get('page', 1, type=int)

    # Calculate the offset based on the page and per_page values
    offset = (page - 1) * 10
    
    # Query the database to get the posts for the current page in descending order
    cursor.execute("""SELECT posts.id, posts.title, posts.content, posts.creation_date, users.username, categories.category_name 
                   FROM posts
                   JOIN users ON users.id = posts.user_id 
                   JOIN categories ON categories.id = posts.category_id
                   ORDER BY posts.last_modified DESC
                   LIMIT ? OFFSET ?;""", (10, offset))
    posts = cursor.fetchall()

    # Query the database to get the total count of posts
    cursor.execute("SELECT COUNT(*) FROM posts;")
    total_posts = cursor.fetchall()[0][0]

    total_pages = (total_posts + 10 - 1) // 10
    
    # Send all posts to partner page
    return render_template("partner.html", posts = posts , total_pages = total_pages, page = page)

@app.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    # Check if method is POST
    if request.method == "POST":
        # Add reply to the database
        cursor.execute("INSERT INTO replies (post_id, user_id, content, creation_date) VALUES (?, ?, ?, ?)", (id, int(session["user_id"]), request.form.get("reply"), date.today()))
        conn.commit()

    # Query database to get the post information
    cursor.execute("""SELECT posts.title, posts.content, posts.creation_date, users.username, categories.category_name
                   FROM posts
                   JOIN users ON users.id = posts.user_id 
                   JOIN categories ON categories.id = posts.category_id
                   WHERE posts.id = ?;""", [int(id)])
    post = cursor.fetchall()

    # Query database to get replies
    cursor.execute("""SELECT replies.content, replies.creation_date, users.username
                   FROM replies
                   JOIN users ON users.id = replies.user_id
                   WHERE post_id = ?""", [int(id)])
    replies = cursor.fetchall()
    return render_template("post.html", post=post, id = id, replies = replies)


@app.route("/create_post", methods=["GET", "POST"])
def create_post():
    # Check if user is logged in
    if session.get("user_id") is None:
        return ("You are not logged in")
    else:
        # If user is logged in check if method is POST
        if request.method == "POST":
            # If method is post ensure the form submitted correctly
            title = request.form.get("title")
            category = request.form.get("category")
            subject = request.form.get("subject")

            if not title:
                return ("No title")
            elif not subject:
                return ("no subject")
            
            # If category submitted correctly find category ID
            if not category:
                return ("no category")
            else:
                cursor.execute("SELECT id FROM categories WHERE category_name = ?", [category])
                category_id = cursor.fetchall()[0][0]
            
            # Submit the post to database
            cursor.execute("INSERT INTO posts (title, content, user_id, category_id, creation_date, last_modified) VALUES (?, ?, ?, ?, ?, ?)", (title, subject, int(session["user_id"]), int(category_id), date.today(), date.today()))
            conn.commit()
        
        # Select all category names from database
        cursor.execute("SELECT category_name FROM categories")
        rows = cursor.fetchall()

        # Render create post template with categories
        return render_template("create_post.html", cats=rows)
    
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
