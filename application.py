import os
import requests
import json
from helpers import *

from flask import Flask, session,render_template,request,redirect,url_for,Markup
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/",methods=["GET","POST"])
@login_required
def index():
    username=session.get('username')
    message=Markup("""<blockquote class="blockquote p-5 mt-5">
    <p>La lectura es para la mente, lo que es el ejercicio para el cuerpo. <br>"Joseph Addison".</p>
  </blockquote>""")
    session["books"]=[]   
    if request.method=="POST":
        message=('')
        text=request.form.get('text') 
        data=db.execute("SELECT * FROM books WHERE author iLIKE '%"+text+"%' OR title iLIKE '%"+text+"%' OR isbn iLIKE '%"+text+"%'").fetchall()
        for x in data:
            session['books'].append(x)
        if len(session["books"])==0:
            message=('No se ha encontrado nada. Intenta de nuevo')
    return render_template("index.html",data=session['books'],message=message,username=username)

@app.route("/isbn/<string:isbn>",methods=["GET","POST"])
@login_required
def bookpage(isbn):
    warning=""
    username=session.get('username') 
    session["reviews"]=[]
    secondreview=db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND username= :username",{"username":username,"isbn":isbn}).fetchone()
    if request.method=="POST" and secondreview==None:
        review=request.form.get('textarea') 
        rating=request.form.get('stars')
        db.execute("INSERT INTO reviews (isbn, review, rating, username) VALUES (:a,:b,:c,:d)",{"a":isbn,"b":review,"c":rating,"d":username})
        db.commit()
    if request.method=="POST" and secondreview!=None:
        warning="Lo siento. No puede agregar una segunda revisión."
    
    res = requests.get("https://www.googleapis.com/books/v1/volumes?q=isbn:"+isbn)
    items =res.json()['items'][0]
    averageRating=items['volumeInfo']['averageRating']
    ratingsCount= items['volumeInfo']['ratingsCount']
    reviews=db.execute("SELECT * FROM reviews WHERE isbn = :isbn",{"isbn":isbn}).fetchall() 
    for y in reviews:
        session['reviews'].append(y)  
    data=db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    return render_template("book.html",data=data,reviews=session['reviews'],averageRating=averageRating,ratingsCount=ratingsCount,username=username,warning=warning)

@app.route("/api/<string:isbn>")
@login_required
def api(isbn):
    data=db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    if data==None:
        return render_template('404.html')
    res = requests.get("https://www.googleapis.com/books/v1/volumes?q=isbn:"+isbn)
    items =res.json()['items'][0]
    averageRating=items['volumeInfo']['averageRating']
    ratingsCount=items['volumeInfo']['ratingsCount']
    x = {
    "title": data.title,
    "author": data.author,
    "year": data.year,
    "isbn": isbn,
    "review_count": ratingsCount,
    "average_score": averageRating
    }
    api=json.dumps(x)
    return render_template("api.json",api=api)

@app.route("/login",methods=["GET","POST"])
def login():
    log_in_message=""    
    if request.method=="POST":
        email=request.form.get('email') 
        userPassword=request.form.get('userPassword')
        emailLogIn=request.form.get('emailLogIn') 
        userPasswordLogIn=request.form.get('userPasswordLogIn')
        if emailLogIn==None:                                  
            data=db.execute("SELECT username FROM users").fetchall()
            for i in range(len(data)):
                if data[i]["username"]==email:
                    log_in_message="Lo siento. El nombre de usuario ya existe."
                    return render_template('login.html',log_in_message=log_in_message)
            db.execute("INSERT INTO users (username,password) VALUES (:a,:b)",{"a":email,"b":userPassword})
            db.commit()
            log_in_message="¡Éxito! Puedes iniciar sesión ahora."
        else:                                                
            data=db.execute("SELECT * FROM users WHERE username = :a",{"a":emailLogIn}).fetchone()
            if data!=None:
                if data.username==emailLogIn and data.password==userPasswordLogIn:
                    session["username"]=emailLogIn
                    return redirect(url_for("index"))
                else:
                    log_in_message="Correo o contraseña equivocada. Intentar otra vez."
            else:
                log_in_message="Correo o contraseña equivocada. Intentar otra vez."
    return render_template('login.html',log_in_message=log_in_message)
         
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))