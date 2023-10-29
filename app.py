# import requirements
from flask import Flask, redirect, render_template, request, session

# Configure Application
app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

@app.route("/")
def index():
    return render_template("index.html", hello = "hello world")
