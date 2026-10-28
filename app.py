from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

# Rutas explícitas para que Render encuentre todo
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.template_folder = os.path.join(BASE_DIR, 'templates')
app.static_folder = os.path.join(BASE_DIR, 'static')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Clave secreta (cámbiala por una propia si quieres)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'cambiar_esta_clave_secreta_12345')

# Base de datos: funciona en Render con PostgreSQL y local con SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    f'sqlite:///{os.path.join(BASE_DIR, "animales.db")}'
).replace('postgres://', 'postgresql://')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Carpeta para guardar fotos
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- Modelos ---
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)


class Animal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    numero = db.Column(db.String(50), unique=True, nullable=False)
    dueno = db.Column(db.String(100))
    peso = db.Column(db.Float)
    raza = db.Column(db.String(100))
    nacimiento = db.Column(db.String(20))
    foto = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'numero': self.numero,
            'dueno': self.dueno,
            'peso': self.peso,
            'raza': self.raza,
            'nacimiento': self.nacimiento,
            'foto': self.foto
        }


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# --- Rutas ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        user = Usuario.query.filter_by(usuario=usuario).first()
        if user and check_password_hash(user.contrasena, contrasena):
            login_user(user)
            return redirect(url_for('index'))
        return render_template('index.html', error='Usuario o contraseña incorrectos')
    return render_template('index.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/api/animales', methods=['GET'])
@login_required
def listar_animales():
    animales = Animal.query.all()
    return jsonify([a.to_dict() for a in animales])


@app.route('/api/animales', methods=['POST'])
@login_required
def crear_animal():
    data = request.form
    foto_archivo = None
    if 'foto' in request.files:
        archivo = request.files['foto']
        if archivo.filename:
            ext = archivo.filename.rsplit('.', 1)[-1].lower()
            nombre_foto = f"{data['numero']}.{ext}"
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_foto)
            archivo.save(ruta)
            foto_archivo = f"/static/uploads/{nombre_foto}"

    animal = Animal(
        nombre=data.get('nombre'),
        numero=data['numero'],
        dueno=data.get('dueno'),
        peso=float(data['peso']) if data.get('peso') else None,
        raza=data.get('raza'),
        nacimiento=data.get('nacimiento'),
        foto=foto_archivo
    )
    db.session.add(animal)
    db.session.commit()
    return jsonify(animal.to_dict()), 201


@app.route('/api/animales/<int:id>', methods=['PUT'])
@login_required
def editar_animal(id):
    animal = Animal.query.get_or_404(id)
    data = request.form
    animal.nombre = data.get('nombre', animal.nombre)
    animal.numero = data.get('numero', animal.numero)
    animal.dueno = data.get('dueno', animal.dueno)
    animal.peso = float(data['peso']) if data.get('peso') else animal.peso
    animal.raza = data.get('raza', animal.raza)
    animal.nacimiento = data.get('nacimiento', animal.nacimiento)

    if 'foto' in request.files:
        archivo = request.files['foto']
        if archivo.filename:
            ext = archivo.filename.rsplit('.', 1)[-1].lower()
            nombre_foto = f"{animal.numero}.{ext}"
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_foto)
            archivo.save(ruta)
            animal.foto = f"/static/uploads/{nombre_foto}"

    db.session.commit()
    return jsonify(animal.to_dict())


@app.route('/api/animales/<int:id>', methods=['DELETE'])
@login_required
def eliminar_animal(id):
    animal = Animal.query.get_or_404(id)
    db.session.delete(animal)
    db.session.commit()
    return jsonify({'mensaje': 'Eliminado correctamente'})


# --- Crear tablas y usuario admin ---
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(usuario='admin').first():
        admin = Usuario(
            usuario='admin',
            contrasena=generate_password_hash('admin123', method='pbkdf2:sha256')
        )
        db.session.add(admin)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)
