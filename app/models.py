from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db, login


class Insumo(db.Model):
    __tablename__ = 'insumos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_producto = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    existencias_iniciales_anio = db.Column(db.Integer, default=0)
    stock_actual = db.Column(db.Integer, default=0)
    porcentaje_utilizado = db.Column(db.Float, default=0.0)
    cantidad_entradas = db.Column(db.Integer, default=0)
    cantidad_salidas = db.Column(db.Integer, default=0)

    # Relaciones
    entradas = db.relationship('EntradaInsumo', backref='insumo', lazy=True)
    salidas = db.relationship('SalidaInsumo', backref='insumo', lazy=True)
    solicitudes = db.relationship('SolicitudInsumo', backref='insumo', lazy=True)
    
    def __repr__(self):
        return f'<Insumo {self.codigo_producto} - {self.descripcion}>'

class EntradaInsumo(db.Model):
    __tablename__ = 'entrada_insumos'
    id_entrada = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha_entrada = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    proveedor = db.Column(db.String(100))
    cantidad = db.Column(db.Integer, nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)

    def __repr__(self):
        return f'<Entrada {self.id_entrada} - Insumo {self.insumo_id}>'

class SalidaInsumo(db.Model):
    __tablename__ = 'salida_insumos'
    id_salida = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    cantidad_entregada = db.Column(db.Integer, nullable=False)
    fecha_salida = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)

    def __repr__(self):
        return f'<Salida {self.id_salida} - Insumo {self.insumo_id}>'

class SolicitudInsumo(db.Model):
    __tablename__ = 'solicitud_insumos'
    id_solicitud = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha_solicitud = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date())
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20))
    observaciones = db.Column(db.String(200))
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)

    def __repr__(self):
        return f'<Solicitud {self.id_solicitud} - Insumo {self.insumo_id} - Estado {self.estado}>'
    


class User(UserMixin,db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cedula = db.Column(db.Integer, unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default='funcionario') # 'admin' o 'funcionario'
    dependencia = db.Column(db.String(100), nullable=False)  

    # Relaciones
    salidas = db.relationship('SalidaInsumo', backref='usuario', lazy=True)
    solicitudes = db.relationship('SolicitudInsumo', backref='usuario', lazy=True)

    def __repr__(self):
        return f'<User {self.nombre}>'
    
    def set_password(self, contraseña):
        self.password = generate_password_hash(contraseña)

    def check_password(self, contraseña):
        return check_password_hash(self.password, contraseña)

    @property
    def id(self):
        return self.id_usuario

@login.user_loader
def load_user(id_usuario):
    return db.session.get(User, int(id_usuario))