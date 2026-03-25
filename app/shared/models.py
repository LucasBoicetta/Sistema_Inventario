from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from sqlalchemy import or_, cast, String, CheckConstraint
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db, login, jwt

# --- Tablas auxiliares ---

class Rol(db.Model):
    __tablename__ = 'roles'
    id_rol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_rol = db.Column(db.String(20), nullable=False, unique=True)

    usuarios = db.relationship('User', backref='rol', lazy=True)

class Dependencia(db.Model):
    __tablename__ = 'dependencia'
    id_dependencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_dependencia = db.Column(db.String(50), nullable=False, unique=True)

    usuarios = db.relationship('User', backref='dependencia', lazy=True)

class Proveedor(db.Model):
    __tablename__ = 'proveedores'
    id_proveedor = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)

    entradas = db.relationship('EntradaInsumo', backref='proveedor', lazy=True)

# --- Tablas principales ---

class Insumo(db.Model):
    __tablename__ = 'insumos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_insumo = db.Column(db.String(10), unique=True, nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    existencias_iniciales_anio = db.Column(db.Integer, default=0)
    stock_actual = db.Column(db.Integer, default=0)
    porcentaje_utilizado = db.Column(db.Integer, default=0)
    cantidad_entradas = db.Column(db.Integer, default=0)
    cantidad_salidas = db.Column(db.Integer, default=0)

    entradas = db.relationship('EntradaInsumo', backref='insumo', lazy=True)
    detalles_solicitud = db.relationship('SolicitudDetalle', backref='insumo', lazy=True)
    salidas = db.relationship('SalidaInsumo', backref='insumo', lazy=True)

    @classmethod
    def filtro_insumos(cls, filtro: str):
        """Método de clase para filtrar insumos por código o descripción."""
        query = cls.query
        if filtro:
            search_str = f"%{filtro}%"
            query = query.filter(
                or_(
                    cls.codigo_insumo.ilike(search_str),
                    cls.descripcion.ilike(search_str)
                )
            )
        return query.order_by(cls.codigo_insumo)


class EntradaInsumo(db.Model):
    __tablename__ = 'entrada_insumos'
    id_entrada = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha_entrada = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    cantidad = db.Column(db.Integer, nullable=False)
    id_insumo = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    id_proveedor = db.Column(db.Integer, db.ForeignKey('proveedores.id_proveedor'), nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cedula = db.Column(db.Integer, unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(256), nullable=False)
    id_rol = db.Column(db.Integer, db.ForeignKey('roles.id_rol'), nullable=False)
    id_dependencia = db.Column(db.Integer, db.ForeignKey('dependencia.id_dependencia'), nullable=False)

    solicitudes = db.relationship('SolicitudInsumo', backref='usuario', lazy=True)
    salidas = db.relationship('SalidaInsumo', backref='usuario', lazy=True)

    def set_password(self, contraseña):
        self.password = generate_password_hash(contraseña)

    def check_password(self, contraseña):
        return check_password_hash(self.password, contraseña)

    @property
    def id(self):
        return self.id_usuario
    
    @property
    def is_authenticated(self):
        return True #Si tengo el objeto User cargardo por JWT, es que está autenticado.

@login.user_loader
def load_user(id_usuario):
    return db.session.get(User, int(id_usuario))

class SolicitudInsumo(db.Model):
    __tablename__ = 'solicitudes'
    id_solicitud = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha_solicitud = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    estado = db.Column(db.Boolean, nullable=False, default=False)  # False: pendiente, True: entregado
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)

    detalles = db.relationship('SolicitudDetalle', backref='solicitud', lazy=True)

    @classmethod
    def obtener_solicitudes_pendientes(cls, filtro: str = None):
        """Devuelve las solicitudes pendientes para que un administrador pueda entregarlas."""
        #Eager load para evitar N+1 queries al mostrar usuario/dependencia.
        query = cls.query.options(
            db.joinedload(cls.usuario).joinedload(User.dependencia)
        ).filter(cls.estado == False)  # Solo pendientes

        if filtro:
            #Intentamos filtrar por número de solicitud.
            if filtro.isdigit():
                query = query.filter(cls.id_solicitud == int(filtro))
            else:
                query = query.join(User).filter(User.nombre.ilike(f"%{filtro}%") )
        
        return query.order_by(cls.fecha_solicitud.asc())


    @classmethod
    def obtener_solicitudes_completadas(cls, id_usuario: int):
        """Devuelve el reporte de las solicitudes entregadas a un usuario."""
        #Lógica: Una solicitud está completa si TODOS sus detalles tienen al menos UNA salida asociada.
        return cls.query.filter(
            cls.id_usuario == id_usuario,
            ~cls.detalles.any(SolicitudDetalle.salidas == None)
        ).order_by(cls.fecha_solicitud.desc())

class SolicitudDetalle(db.Model):
    __tablename__ = 'solicitudes_insumos'
    id_solicitudes_insumos = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    id_solicitud = db.Column(db.Integer, db.ForeignKey('solicitudes.id_solicitud'), nullable=False)
    id_insumo = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    
    salidas = db.relationship('SalidaInsumo', backref='solicitud_detalle', lazy=True)

class SalidaInsumo(db.Model):
    __tablename__ = 'salidas_insumos'
    id_salida = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cantidad_entregada = db.Column(db.Integer, nullable=False)
    fecha_salida = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    observaciones = db.Column(db.String(150))
    id_insumo = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    id_solicitudes_insumos = db.Column(db.Integer, db.ForeignKey('solicitudes_insumos.id_solicitudes_insumos'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)

    @classmethod
    def filtro_salidas_insumos(cls, filtro: str):
        """Método para filtrar salidas de insumos por usuario, dependencia codigo o descripción"""
        #1. Query base con Eager Loading (para performance al mostrar).
        query = cls.query.options(
            db.joinedload(cls.usuario).joinedload(User.dependencia),
            db.joinedload(cls.insumo)
        )
        #2. Join explícitos.
        query = query.join(User).join(Insumo).join(Dependencia)

        if filtro:
            search_str = f"%{filtro}%"
            query = query.filter(
                or_(
                    cast(cls.fecha_salida, String).ilike(search_str), #Permitir búsqueda por fecha (formato YYYY-MM-DD)
                    User.nombre.ilike(search_str),
                    Dependencia.nombre_dependencia.ilike(search_str),
                    Insumo.codigo_insumo.ilike(search_str),
                    Insumo.descripcion.ilike(search_str)
                )
            )
            
        return query.order_by(cls.fecha_salida.desc())