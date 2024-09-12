from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import String, Integer, Float, Column, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Relationship, relationship
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from wtforms import StringField, FloatField, IntegerField, SubmitField, PasswordField
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
import requests
import os

API_KEY = os.environ.get('API_KEY')

app = Flask(__name__)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)
class Base(DeclarativeBase):
    pass

app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
Bootstrap5(app)

class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///movies.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

class UserMovie(db.Model):
    __tablename__ = 'user_movies'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    rating = db.Column(db.Float, nullable=True)
    review = db.Column(db.String(250), nullable=True)

    user = db.relationship('User', back_populates='user_movies')
    movie = db.relationship('Movies', back_populates='user_movies')

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(1000), nullable=False)
    user_movies = db.relationship('UserMovie', back_populates='user')

class Movies(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    img_url = db.Column(db.String(1000), nullable=False)
    user_movies = db.relationship('UserMovie', back_populates='movie')

with app.app_context():
    db.create_all()

class EditMovies(FlaskForm):
    rating = FloatField(label="Add Your Rating Out Of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField(label="Add Your Review", validators=[DataRequired()])
    submit = SubmitField(label="Submit")

class AddMovies(FlaskForm):
    title = StringField(label="Movie Title")
    submit = SubmitField(label="Add new movie")

class Register(FlaskForm):
    username = StringField(label="Choose a username", validators=[DataRequired()])
    email = StringField(label="Enter your email address", validators=[DataRequired()])
    password = PasswordField(label="Create a password", validators=[DataRequired()])
    submit = SubmitField(label="Register")

class Login(FlaskForm):
    email = StringField(label="Enter your email address", validators=[DataRequired()])
    password = PasswordField(label="Enter your password", validators=[DataRequired()])
    submit = SubmitField(label="Login")

class ChangeTitle(FlaskForm):
    title = StringField(label="New title", validators=[DataRequired()])
    submit = SubmitField(label="Save changes")

class ChangeSubTitle(FlaskForm):
    title = StringField(label="New subtitle", validators=[DataRequired()])
    submit = SubmitField(label="Save changes")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.name == 'Admin' and current_user.email == 'admin@gmail.com':
            return f(*args, **kwargs)
        else:
            flash("You must be an admin to access this page.", category='warning')
            return redirect(url_for('home'))
    return decorated_function


# second_movie = Movies(
#     title="Avatar The Way of Water",
#     year=2022,
#     description="Set more than a decade after the events of the first film, learn the story of the Sully family (Jake, Neytiri, and their kids), the trouble that follows them, the lengths they go to keep each other safe, the battles they fight to stay alive, and the tragedies they endure.",
#     rating=7.3,
#     ranking=9,
#     review="I liked the water.",
#     img_url="https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg"
# )
# with app.app_context():
#     db.session.add(second_movie)
#     db.session.commit()


@app.route("/")
def home():
    is_admin = current_user.is_authenticated and current_user.email == 'admin@gmail.com'

    return render_template('index.html', is_loggedin=current_user.is_authenticated, is_admin=is_admin, is_home=True)


@app.route("/favorite-movies", methods=["POST", "GET"])
def user_movies():
    user_movie_entries = db.session.execute(
        db.select(UserMovie).where(UserMovie.user_id == current_user.id)
    ).scalars().all()

    movies = [entry.movie for entry in user_movie_entries]

    for entry in user_movie_entries:
        movie = next((m for m in movies if m.id == entry.movie_id), None)
        if movie:
            movie.user_movie = entry

    movies = sorted(movies, key=lambda movie: movie.user_movie.rating if movie.user_movie else 0, reverse=True)

    for num in range(len(movies)):
        movies[num].ranking = num + 1

    db.session.commit()

    return render_template('users_movies.html', movies=movies, is_loggedin=current_user.is_authenticated, is_true=True)


@app.route("/edit/<int:movie_id>", methods=["POST", "GET"])
@login_required
def edit(movie_id):
    form = EditMovies()
    user_movie = db.session.execute(
        db.select(UserMovie).where(UserMovie.user_id == current_user.id, UserMovie.movie_id == movie_id)
    ).scalar()

    if request.method == "POST" and form.validate_on_submit():
        if user_movie:
            user_movie.rating = form.rating.data
            user_movie.review = form.review.data
        else:
            user_movie = UserMovie(
                user_id=current_user.id,
                movie_id=movie_id,
                rating=form.rating.data,
                review=form.review.data
            )
            db.session.add(user_movie)

        db.session.commit()
        return redirect(url_for('user_movies'))

    movie = db.session.execute(db.select(Movies).where(Movies.id == movie_id)).scalar()
    return render_template('edit.html', form=form, movie=movie, user_movie=user_movie,
                           is_loggedin=current_user.is_authenticated)


@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):
    movie = db.session.execute(
        db.select(Movies).where(Movies.id == movie_id)
    ).scalar()

    if not movie:
        flash("Movie not found.", "warning")
        return redirect(url_for('explore'))

    return render_template("movie_details.html", movie=movie, is_loggedin=current_user.is_authenticated)


@app.route("/profiles")
def profiles():
    users = db.session.execute(db.select(User)).scalars().all()
    return render_template('profiles.html', users=users, is_loggedin=current_user.is_authenticated, is_explore=True)


@app.route("/delete/<int:movie_id>")
@login_required
def delete(movie_id):
    user_movie = db.session.execute(
        db.select(UserMovie).where(UserMovie.user_id == current_user.id, UserMovie.movie_id == movie_id)
    ).scalar()

    if user_movie:
        db.session.delete(user_movie)
        db.session.commit()

    return redirect(url_for('user_movies'))


@app.route("/add", methods=["POST", "GET"])
@login_required
def add_movies():
    form = AddMovies()

    if request.method == "POST" and form.validate_on_submit():
        movie_title = form.title.data
        url = "https://api.themoviedb.org/3/search/movie?language=en-US&page=1"
        api_key = API_KEY

        response = requests.get(url, params={"api_key": api_key, "query": movie_title})
        data = response.json()["results"]
        return render_template("select.html", movies=data, is_loggedin=current_user.is_authenticated)

    return render_template('add_movie.html', form=form, is_loggedin=current_user.is_authenticated)


@app.route("/select/<int:search_id>")
@login_required
def select(search_id):
    url = f"https://api.themoviedb.org/3/movie/{search_id}?language=en-US"
    api_key = API_KEY

    response = requests.get(url, params={'api_key': api_key})
    data = response.json()

    existing_movie = db.session.execute(
        db.select(Movies).where(Movies.title == data["title"])
    ).scalar()

    if not existing_movie:
        new_movie = Movies(
            title=data["title"],
            year=data["release_date"],
            description=data["overview"],
            img_url=f"https://image.tmdb.org/t/p/original{data['poster_path']}",
        )
        db.session.add(new_movie)
        db.session.commit()
        existing_movie = new_movie

    user_movie_entry = db.session.execute(
        db.select(UserMovie).where(UserMovie.user_id == current_user.id, UserMovie.movie_id == existing_movie.id)
    ).scalar()

    if not user_movie_entry:
        user_movie_entry = UserMovie(user_id=current_user.id, movie_id=existing_movie.id)
        db.session.add(user_movie_entry)
        db.session.commit()

    return redirect(url_for('edit', movie_id=existing_movie.id))


@app.route("/register", methods=["POST", "GET"])
def register():
    form = Register()

    if request.method == "POST" and form.validate_on_submit():
        user_name = form.username.data
        email = form.email.data
        password = form.password.data

        username = db.session.execute(db.select(User).where(User.name == user_name)).scalar()
        user_email = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if username:
            flash("This username is already taken. Please choose a different one.", category='warning')
        elif user_email:
            flash("This email is already registered. Please use a different email or log in.", category='warning')
        else:
            flash('Registration successful!', 'success')
            hash_password = generate_password_hash(password,
                                                   method="pbkdf2:sha256",
                                                   salt_length=10)
            new_user = User(
                name=user_name,
                email=email,
                password=hash_password,
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))


    return render_template('register.html', form=form)


@app.route("/login", methods=["POST", "GET"])
def login():
    form = Login()

    if request.method == "POST" and form.validate_on_submit():
        email = form.email.data
        user_password = form.password.data

        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user is None:
            flash("The email you entered is not registered. Please check the email or register for an account.", category='info')
        elif not check_password_hash(user.password, user_password):
            flash("The password you entered is incorrect. Please try again.", category='danger')
        else:
            flash('Login successful! Welcome back.', 'success')
            login_user(user)
            return redirect(url_for('home'))
    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=False)