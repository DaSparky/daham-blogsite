import os
import smtplib
from datetime import date
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8jhBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
app.app_context().push()

my_mail = os.environ['EMAIL']
my_pass = os.environ['PASSWORD']


# CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship('BlogPost', back_populates='author')

    # "comment_author" refers to the comment_author property in the Comment class.
    user_comments = relationship('Comment', back_populates='comment_author')


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship('User', back_populates='posts')

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    post_comments = relationship('Comment', back_populates='parent_post')


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    # "users.id" The users refers to the tablename of the Users class.
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # "user_comments" refers to the comments property in the User class.
    comment_author = relationship('User', back_populates='user_comments')

    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    parent_post = relationship('BlogPost', back_populates='post_comments')

    text = db.Column(db.Text, nullable=False)


@login_manager.user_loader
def user_load(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def wrapper_func(*args, **kwargs):
        # If user is not logged in OR id is not 1 then return abort with 403 error
        if current_user.is_anonymous or current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return wrapper_func


@app.route('/')
def get_all_posts():
    print(current_user)
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=request.form['email']).first():
            flash("This Email is already registered!, Try Login instead.")
            return redirect(url_for('login'))

        new_user = User()
        new_user.name = form.data['name']
        new_user.email = form.data['email']
        new_user.password = generate_password_hash(password=form.data['password'], method='pbkdf2:sha256',
                                                   salt_length=8)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form_login = LoginForm()
    if form_login.validate_on_submit():
        user = User.query.filter_by(email=request.form['email']).first()
        if user:
            if check_password_hash(user.password, request.form['password']):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Wrong Password, Try again!')
                return redirect(url_for('login'))
        else:
            flash('This Email is invalid!')
            return redirect(url_for('login'))
    return render_template("login.html", form=form_login)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    gravatar = Gravatar(app,
                        size=100,
                        rating='g',
                        default='retro',
                        force_default=False,
                        force_lower=False,
                        use_ssl=False,
                        base_url=None)
    requested_post = BlogPost.query.get(post_id)
    post_comments = [comment for comment in Comment.query.filter_by(post_id=post_id).all()]
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=comment_form.comment.data,
                comment_author=current_user,
                parent_post=requested_post,
            )
            db.session.add(new_comment)
            db.session.commit()
            redirect(url_for('show_post'))
        else:
            flash('You need to Login to comment')
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, comments=post_comments, form=comment_form,
                           gravatar=gravatar)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=['GET', 'POST'])
@login_required
def contact():
    if request.method == 'POST':
        user_feedback = f"Name: {request.form['name']}\nEmail: {request.form['email']}\nMessage: {request.form['message']}"
        with smtplib.SMTP("smtp.zoho.com", port=587) as connection:
            connection.starttls()
            connection.login(user=my_mail, password=my_pass)
            connection.sendmail(from_addr=my_mail, to_addrs="daham31con@gmail.com",
                                msg=f"Subject:Feedback BlogTest site"
                                    f"\n\n{user_feedback}")
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author.name,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author.name = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
