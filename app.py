# Bibliotecas
from flask import Flask, render_template, request, redirect, url_for, flash, g, session
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.menu import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import logging
import sqlite3
import plotly.graph_objects as go
from shows import shows_list
import json


# Instancia do Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
app.permanent_session_lifetime = timedelta(minutes=10)

# Configurando o banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuario.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['SECRET_KEY'] = 'chave-secreta'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
logging.basicConfig(filename='app.log', level=logging.INFO)

app.config.from_object(__name__)

#Instância do SQLAlchemy
db = SQLAlchemy(app)


#-----INGRESSO-----
# Classe show
class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    available_tickets = db.Column(db.Integer, nullable=False)

    tickets = db.relationship('Ticket', backref='show', lazy=True)

    def __repr__(self):
        return f'<Show {self.artist}>'
    
# Classe ingresso
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Ticket {self.name}>'

# -----TELA DE LOGIN-----
# Modelo do usuário
class Usuario(db.Model,  UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True)
    senha = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20))
    
    # Gerar o hash da senha
    def definir_senha(self, senha):
        self.password_hash = generate_password_hash(senha)

    # Verificar se a senha do usuário está correta
    def verificar_senha(self, senha):
        return check_password_hash(self.password_hash, senha)



class UserView(ModelView):
    column_list = ('nome', 'email', 'role')
    form_columns = ('nome', 'email', 'password', 'role')
    form_extra_fields = {
        'password': PasswordField('Senha', validators=[DataRequired(), Length(min=4)])
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.definir_senha(form.password.data)
        else:
            # Atualizar a senha apenas se um novo valor for fornecido
            if form.password.data:
                model.definir_senha(form.password.data)
            else:
                # Recuperar a senha atual do banco de dados
                current_password = Usuario.query.get(model.id).password_hash
                model.password_hash = current_password  # Manter a senha atual

        db.session.commit()

# Classe para o formulário de login
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Submit')

class LogoutMenuLink(MenuLink):
    def is_accessible(self):
        return current_user.is_authenticated
    
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        # Redirecionar para a página de login caso o acesso seja negado
        return redirect(url_for('login'))

    @expose('/')
    def index(self):
        self._template_args['logout_link'] = LogoutMenuLink('Logout', endpoint='logout')
        return super(MyAdminIndexView, self).index()

    def _configure_menu(self):
        # Adicionar o link de logout ao menu
       self._menu.append(MenuLink('Logout', '/logout'))

# Configurações para o painel do Admin
admin = Admin(app, name='Admin', template_mode='bootstrap3', index_view=MyAdminIndexView())
admin.add_link(LogoutMenuLink(name='Logout', endpoint='logout'))
admin.add_view(UserView(Usuario, db.session))
admin.add_link(MenuLink('Gráfico de Usuários', endpoint='users_chart'))

# Função para carregar o usuário
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))



# -----TELA DE LOGIN-----
# Formulário de registro de usuários
class RegistroForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    confirmar_senha = PasswordField('Confirmar senha', validators=[DataRequired(), EqualTo('senha')])
    enviar = SubmitField('Registrar')


# -----TELA DE LOGIN-----
# Rota inicial
@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        remaining_time = session.get('remaining_time')  # Obtém o valor da variável 'remaining_time' da sessão
        if current_user.role == 'admin':
            return redirect(url_for('admin.index', remaining_time=remaining_time))
        else:
            return render_template('index.html', remaining_time=remaining_time)
    else:
        return redirect(url_for('index'))
    
@app.route('/login', methods=['GET', 'POST'])
def logi():
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(email=form.email.data).first()
        if user and user.verificar_senha(form.senha.data):
            login_user(user, remember=form.remember.data)
            session.permanent = True  # Definir a sessão como permanente
            session['last_activity'] = datetime.now()  # Atualiza o tempo da última atividade
            # Calcular a data e hora de expiração da sessão
            session['expiration'] = datetime.now() + timedelta(minutes=10)
            # Registro no arquivo de log
            logging.info('Usuário {} fez logout'.format(current_user.nome))# Corrigido aqui
            return redirect(url_for('index'))
        else:
            flash('Nome de usuário ou senha incorretos', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logging.info('Usuário {} fez logout'.format(current_user.nome))
    logout_user()
    session.pop('permanent', None) # Remover a marca de sessão permanente
    return redirect(url_for('login'))


@app.route('/create_user', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    # Cria o objeto User com a senha já hasheada
    user = Usuario(username=username, email=email, role=role)
    user.definir_senha(password)

    db.session.add(user)
    db.session.commit()

    flash('Usuário criado com sucesso', 'success')
    return redirect(url_for('admin.index'))

@app.before_request
def before_request():
    if current_user.is_authenticated:
        now = datetime.now(timezone.utc).astimezone()
        if 'expiration' not in session or session['expiration'] < now:
            session['expiration'] = now + app.permanent_session_lifetime
            session['remaining_time'] = app.permanent_session_lifetime.total_seconds() // 60
        else:
            remaining_time = session['expiration'] - now
            session['remaining_time'] = remaining_time.seconds // 60
    else:
        session.pop('expiration', None)
        session.pop('remaining_time', None)


@app.route('/users_chart')
@login_required
def users_chart():
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('index'))

    # Consulta o total de usuários por função
    roles = db.session.query(Usuario.role, db.func.count()).group_by(Usuario.role).all()
    labels = [role[0] for role in roles]
    values = [role[1] for role in roles]

    # Configuração das barras
    bar_data = {
        'x': labels,
        'y': values,
        'type': 'bar',
        'marker': {
            'color': ['rgb(31, 119, 180)', 'rgb(255, 127, 14)', 'rgb(44, 160, 44)', 'rgb(214, 39, 40)'],
            'line': {
                'color': 'rgb(8, 48, 107)',
                'width': 1.5
            }
        }
    }

    # Cria o gráfico de barras
    chart_data = {
        'data': [bar_data],
        'layout': {
            'title': 'Total de Usuários por Função',
            'xaxis': {'title': 'Função'},
            'yaxis': {'title': 'Total'},
            'template': 'plotly_white'
        }
    }

    # Converte para JSON
    chart_data_json = json.dumps(chart_data)

    return render_template('users_chart.html', chart_data=chart_data_json)

# -----TELA DE LOGIN-----
# Rota de registro de usuários
@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    form = RegistroForm()
    if form.validate_on_submit():
        nome = form.nome.data
        email = form.email.data
        senha = form.senha.data

        usuario = Usuario(nome=nome, email=email, senha=senha)
        db.session.add(usuario)
        db.session.commit()

        flash('Registro realizado com sucesso!')
        return redirect(url_for('login'))
    return render_template('registrar.html', form=form)

@app.route('/comprador')
@login_required
def comprador():
    if current_user.role == 'comprador':
        return render_template('index.html')
    else:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('index'))
    
    
# -----TELA DE LOGIN-----
# Formulário de login de usuários


# Retorna uma conexão com o banco de dados SQLite
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db

#Encerra a conexão com o banco de dados quando a aplicação é finalizada
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Rota para a página inicial
@app.route('/index', methods=['GET', 'POST'])
def index():
    with app.app_context():
        shows = Show.query.all()
        return render_template('index.html', shows=shows)


#Rota para a página de cadastro de notas
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            show_id = request.form['show_id']
            quantity = request.form['quantidade']

            # Validar a quantidade
            try:
                quantity = int(quantity)
            except ValueError:
                return 'A quantidade deve ser um número inteiro.'

            # Verificar se o show já existe
            show = Show.query.filter_by(id=show_id).first()
            if not show:
                return 'O show selecionado não existe.'

            # Verificar se ainda há ingressos disponíveis
            if show.available_tickets < quantity:
                return 'Não há ingressos suficientes disponíveis para este show.'

            # Decrementar o número de ingressos disponíveis
            show.available_tickets -= quantity
            db.session.commit()

            ticket = Ticket(name=name, email=email, show_id=show_id, quantity=quantity)
            db.session.add(ticket)
            db.session.commit()

            return redirect(url_for('index'))

    shows = Show.query.all()
    return render_template('cadastro.html', shows=shows)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        for show_data in shows_list:
            artist = show_data['artist']
            date = show_data['date']
            time = show_data['time']
            location = show_data['location']
            price = show_data['price']
            available_tickets = show_data['available_tickets']

            # Verificar se o show já existe
            existing_show = Show.query.filter_by(artist=artist, date=date, location=location, time=time).first()

            if existing_show:
                print(f"Show {artist} em {location} no dia {date} às {time} já existe na base de dados.")
            else:
                if available_tickets < 0:
                    available_tickets = 0

                show = Show(artist=artist, date=date, time=time, location=location, price=price, available_tickets=available_tickets)
                db.session.add(show)
                db.session.commit()

                print(f"Show {artist} em {location} no dia {date} às {time} com ingresso a {price} adicionado com sucesso à base de dados.")
        
        if not Usuario.query.filter_by(role='admin').first():
            admin_user = Usuario(nome='Admin', email='admin@example.com', senha='admin', role='admin')
            admin_user.definir_senha('admin')
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=True)