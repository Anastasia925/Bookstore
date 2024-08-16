from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_admin.contrib.sqla import ModelView
from flask_admin import BaseView, expose
from datetime import datetime, timezone
from hashlib import md5
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from time import time
import jwt
from app import app, admin, db, login


class Exit(BaseView):
    """Вкладка админ панели"""

    @expose('/')
    def exit_page(self):
        return self.render('admin/exit_page/index.html')


class User(db.Model, UserMixin):
    """Модель пользователя"""
    __tablename__ = 'users'
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), nullable=False, unique=True, index=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    telegram: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                                unique=True, default=None)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))
    orders = relationship("Order")  # one to many to Order

    def __repr__(self):
        return self.login

    def set_password(self, password):
        """
        Password replacement function
        :param password: user password
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Password verification function
        :param password: user password
        :return: boolean
        """
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        """
        The function of get a token to reset the password
        :return: JWT token: str
        """
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        """
        Token decoding method
        :return: User if token else None
        """
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return db.session.get(User, id)

    def avatar(self, size):
        """
        Avatar generation function.
        Default size = 80x80.
        :param size: size of the avatar (s=128 == 128x128)
        :return: link: str (maybe custom)
        """
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'


class Order(db.Model):
    """Модель заказа"""
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(10))
    start_rent = db.Column(db.DateTime(), default=datetime.utcnow)
    end_rent = db.Column(db.DateTime(), default=None)
    user_id = db.Column(db.Integer, ForeignKey('users.id'))  # многие к одному к User
    book = relationship("Book", uselist=False)  # один к одному к Book


class Book(db.Model):
    """Модель книги"""
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    author = db.Column(db.String(50))
    year = db.Column(db.Integer)
    image_link = db.Column(db.String(200))
    filename = db.Column(db.String(30))
    order = db.Column(db.Integer, ForeignKey('orders.id'))  # один к одному к Order

    def __repr__(self):
        return self.name


# Adding in admin panel
admin.add_view(ModelView(User, db.session, name='Пользователи'))
admin.add_view(ModelView(Book, db.session, name='Книги'))
admin.add_view(ModelView(Order, db.session, name='Заказы'))
admin.add_view(Exit(name='Выход', endpoint='exit'))


@login.user_loader
def load_user(id):
    """
    The function will configure the user loader function,
    which can be called to load a user with an ID
    :param id: user ID
    """
    return db.session.get(User, int(id))

