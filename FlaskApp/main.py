from flask import Flask, make_response, request, redirect, render_template, jsonify
from data import db_session
from data import users
from data import products
import datetime
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from loginform import LoginForm, RegisterForm, NewsForm
from werkzeug.exceptions import abort
import news_api, news_resources
from flask_restful import Api

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)
login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)


@app.route("/")
def head():
    return render_template('main.html')


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(users.User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/product")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = users.User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route("/product")
def index():
    session = db_session.create_session()
    if current_user.is_authenticated:
        news = session.query(products.Products).filter(
            (products.Products.user == current_user) | (products.Products.is_private == 0))
    else:
        news = session.query(products.Products).filter(products.Products.is_private == 0)
    return render_template("index.html", news=news)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/product")


@app.route('/news',  methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        news = products.Products()
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        session.merge(current_user)
        session.commit()
        return redirect('/product')
    return render_template('products.html', title='Добавление продукта',
                           form=form)


@app.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == "GET":
        session = db_session.create_session()
        news = session.query(products.Products).filter(products.Products.id == id,
                                                       products.Products.user == current_user).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        news = session.query(products.Products).filter(products.Products.id == id,
                                                       products.Products.user == current_user).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            session.commit()
            return redirect('/product')
        else:
            abort(404)
    return render_template('products.html', title='Редактирование товара', form=form)


@app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    session = db_session.create_session()
    news = session.query(products.Products).filter(products.Products.id == id,
                                                   products.Products.user == current_user).first()
    if news:
        session.delete(news)
        session.commit()
    else:
        abort(404)
    return redirect('/product')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route("/courier")
def courier():
    return render_template('courier.html')


def main():
    db_session.global_init("db/blogs0.sqlite")
    #app.register_blueprint(news_api.blueprint)
    api.add_resource(news_resources.NewsListResource, '/api/v2/news')
    api.add_resource(news_resources.NewsResource, '/api/v2/news/<int:news_id>')
    app.run()


if __name__ == '__main__':
    main()