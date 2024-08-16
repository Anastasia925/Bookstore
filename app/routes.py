import flask_login
import os
import io
import datetime
from urllib.parse import urlsplit
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User, Book, Order

# for pay
from cloudipsp import Api, Checkout


@app.before_request
def before_request():
    """The function of updating the last visit"""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    """The function of the main page"""
    books = Book.query.order_by(Book.price).all()
    return render_template('index.html', title='Главная', data=books)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Account login function
    :return: index or login pages
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Некорректное имя или пароль')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Account register function
    :return: register or login pages
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, telegram=form.telegram.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Вы зарегистрированы')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    """
    Profile function
    :param username: str
    :return: render profile and data
    """
    user = db.first_or_404(sa.select(User).where(User.username == username))
    orders = flask_login.current_user.orders
    time_now = datetime.datetime.now()
    return render_template('user.html', user=user, data=orders, now=time_now)


@app.route('/logout')
def logout():
    """
    Account logout function
    :return: index page
    """
    logout_user()
    return redirect(url_for('index'))


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('login_page') + '?next=' + request.url)

    return response


@app.errorhandler(404)
def error404(error):
    """Функция-обработчик ошибки отсутствия страницы"""
    return render_template('404.html')


@app.route('/buy/<int:id>')
def book_buy(id):
    """
    Функция покупки. Необходим VPN.

    merchant_id: from account in Fondy
    :param id: id книги
    :return: url transaction
    """
    book = Book.query.get(id)  # get book.id from database

    api = Api(merchant_id=1396424,
              secret_key='test')
    checkout = Checkout(api=api)
    data = {
        "currency": "USD",
        "amount": str(book.price) + '00'
    }
    url = checkout.url(data).get('checkout_url')

    user_id = flask_login.current_user.id
    book_id = id
    status = 'buy'
    new_order = Order(status=status, user_id=user_id, book=book)
    db.session.add(new_order)
    db.session.commit()
    return redirect(url)


@app.route('/rent/<int:days>/<int:id>')
def book_rent(days: int, id: int):
    """
    Функция аренды. Необходим VPN.

    merchant_id: from account in Fondy
    :param days: количество дней
    :param id: id книги
    :return: url transaction
    """
    book = Book.query.get(id)  # get book.id from database

    api = Api(merchant_id=1396424,
              secret_key='test')
    checkout = Checkout(api=api)
    data = {
        "currency": "USD",
        "amount": str(book.price) + '00'
    }
    url = checkout.url(data).get('checkout_url')

    user_id = flask_login.current_user.id
    status = 'rent'
    end_rent = (datetime.datetime.utcnow() + datetime.timedelta(days=days))
    new_order = Order(status=status, user_id=user_id, book=book, end_rent=end_rent)
    db.session.add(new_order)
    db.session.commit()
    return redirect(url)


@app.route('/reed/<int:id>', methods=['GET'])
@login_required
def reed(id):
    book = db.session.query(Book).get(id)
    text = os.path.abspath(os.path.join(os.path.dirname(__file__), 'books_files', book.filename))

    with io.open(text, encoding='utf-8') as file:
        return render_template('read.html', data=book, text=file.readlines())
