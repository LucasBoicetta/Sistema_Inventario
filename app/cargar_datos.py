import random
from datetime import datetime
from app import app, db
from app.models import User, Rol, Dependencia, Insumo, Proveedor, SolicitudInsumo, SolicitudDetalle, EntradaInsumo, SalidaInsumo

def seed_data():
    with app.app_context():
        # Limpiar tablas
        db.session.query(SalidaInsumo).delete()
        db.session.query(EntradaInsumo).delete()
        db.session.query(SolicitudDetalle).delete()
        db.session.query(SolicitudInsumo).delete()
        db.session.query(User).delete()
        db.session.query(Rol).delete()
        db.session.query(Dependencia).delete()
        db.session.query(Insumo).delete()
        db.session.query(Proveedor).delete()
        db.session.commit()

        # Roles y dependencias
        rol_admin = Rol(nombre_rol='admin')
        rol_usuario = Rol(nombre_rol='usuario')
        db.session.add_all([rol_admin, rol_usuario])
        deps = [Dependencia(nombre_dependencia=n) for n in [
            'Recursos Humanos', 'Contabilidad', 'Tecnología', 'Dirección', 'Jurídica','Informática']]
        db.session.add_all(deps)
        db.session.commit()

        # Usuarios
        admin = User(nombre='admin', cedula='100', id_rol=rol_admin.id_rol, id_dependencia=deps[3].id_dependencia)
        admin.set_password('admin')
        db.session.add(admin)
        usuarios = []
        for i in range(1, 11):
            u = User(
                nombre=f'Usuario{i}',
                cedula=str(100+i),
                id_rol=rol_usuario.id_rol,
                id_dependencia=random.choice(deps).id_dependencia
            )
            u.set_password('usuario')
            usuarios.append(u)
        db.session.add_all(usuarios)
        db.session.commit()

        # Proveedor
        proveedor = Proveedor(nombre='Proveedor Oficial')
        db.session.add(proveedor)
        db.session.commit()

        # Insumos
        insumos_data = [
            ('INS001', 'Resma de Papel A4'), ('INS002', 'Bolígrafo Azul'), ('INS003', 'Bolígrafo Negro'),
            ('INS004', 'Toner HP'), ('INS005', 'Carpeta Colgante'), ('INS006', 'Clips'),
            ('INS007', 'Grapadora'), ('INS008', 'Grapas'), ('INS009', 'Notas Adhesivas'),
            ('INS010', 'Cinta Adhesiva'), ('INS011', 'Tijeras'), ('INS012', 'Resaltador'),
            ('INS013', 'Borrador'), ('INS014', 'Pilas AA'), ('INS015', 'Sobre Oficio')
        ]
        insumos = []
        for cod, desc in insumos_data:
            stock = random.randint(50, 100)
            insumo = Insumo(
                codigo_insumo=cod,
                descripcion=desc,
                existencias_iniciales_anio=stock,
                cantidad_entradas=stock,
                cantidad_salidas=0,
                stock_actual=stock,
                porcentaje_utilizado=0.0
            )
            db.session.add(insumo)
            db.session.flush()
            entrada = EntradaInsumo(
                id_proveedor=proveedor.id_proveedor,
                cantidad=stock,
                id_insumo=insumo.id
            )
            db.session.add(entrada)
            insumos.append(insumo)
        db.session.commit()

        # Solicitudes y entregas
        for usuario in usuarios[:5]:  # 5 usuarios hacen solicitudes
            solicitud = SolicitudInsumo(id_usuario=usuario.id_usuario, estado=False)
            db.session.add(solicitud)
            db.session.flush()
            insumos_solicitados = random.sample(insumos, 3)
            detalles = []
            for insumo in insumos_solicitados:
                cantidad = random.randint(1, 5)
                detalle = SolicitudDetalle(
                    id_solicitud=solicitud.id_solicitud,
                    id_insumo=insumo.id,
                    cantidad_solicitada=cantidad
                )
                db.session.add(detalle)
                detalles.append((detalle, insumo, cantidad))
            db.session.commit()
            # Simular entrega por admin
            for detalle, insumo, cantidad in detalles:
                if insumo.stock_actual >= cantidad:
                    salida = SalidaInsumo(
                        cantidad_entregada=cantidad,
                        id_usuario=usuario.id_usuario,
                        id_insumo=insumo.id,
                        id_solicitudes_insumos=detalle.id_solicitudes_insumos,
                        observaciones='Entrega de prueba'
                    )
                    db.session.add(salida)
                    insumo.stock_actual -= cantidad
                    insumo.cantidad_salidas += cantidad
                    total_inicial = insumo.existencias_iniciales_anio + insumo.cantidad_entradas
                    if total_inicial > 0:
                        insumo.porcentaje_utilizado = (insumo.cantidad_salidas / total_inicial) * 100
            solicitud.estado = True
            db.session.commit()

        print("Base de datos poblada con datos de prueba.")

if __name__ == '__main__':
    seed_data()