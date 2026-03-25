import random
from datetime import datetime, timedelta
from app import app, db
from app.shared.models import User, Rol, Dependencia, Insumo, Proveedor, SolicitudInsumo, SolicitudDetalle, EntradaInsumo, SalidaInsumo

def seed_data():
    with app.app_context():
        print("Limpiando base de datos...")
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

        print("Creando roles y dependencias...")
        # Roles
        rol_admin = Rol(nombre_rol='admin')
        rol_usuario = Rol(nombre_rol='usuario')
        db.session.add_all([rol_admin, rol_usuario])
        
        # Dependencias de una institución pública real
        dependencias_nombres = [
            'Dirección General', 'Recursos Humanos', 'Contabilidad', 'Tesorería',
            'Tecnología de la Información', 'Auditoría Interna', 'Jurídica',
            'Planificación', 'Comunicación', 'Servicios Generales',
            'Archivo y Documentación', 'Mesa de Entrada', 'Compras y Contrataciones',
            'Patrimonio', 'Secretaría Privada'
        ]
        deps = [Dependencia(nombre_dependencia=n) for n in dependencias_nombres]
        db.session.add_all(deps)
        db.session.commit()

        print("Creando 100 funcionarios...")
        # Administradores (5)
        admins = []
        for i in range(5):
            admin = User(
                nombre=f'Admin{i+1}',
                cedula=str(1000 + i),
                id_rol=rol_admin.id_rol,
                id_dependencia=random.choice(deps).id_dependencia
            )
            admin.set_password('admin')
            admins.append(admin)
        db.session.add_all(admins)
        
        # Usuarios regulares (95)
        usuarios = []
        nombres = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Pedro', 'Sofía', 
                   'Diego', 'Valentina', 'Miguel', 'Camila', 'José', 'Lucía', 'Pablo']
        apellidos = ['González', 'Rodríguez', 'Martínez', 'García', 'López', 'Fernández',
                     'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores', 'Díaz']
        
        for i in range(95):
            nombre = f"{random.choice(nombres)} {random.choice(apellidos)}"
            u = User(
                nombre=nombre,
                cedula=str(2000 + i),
                id_rol=rol_usuario.id_rol,
                id_dependencia=random.choice(deps).id_dependencia
            )
            u.set_password('usuario')
            usuarios.append(u)
        db.session.add_all(usuarios)
        db.session.commit()

        print("Creando proveedores...")
        # Proveedores
        proveedores_nombres = [
            'Librería Central S.A.', 'Distribuidora Office Max', 'Papelería El Estudiante',
            'Tecnología y Oficina', 'Suministros Industriales'
        ]
        proveedores = [Proveedor(nombre=n) for n in proveedores_nombres]
        db.session.add_all(proveedores)
        db.session.commit()

        print("Creando 50 tipos de insumos...")
        # 50 Insumos de oficina realistas
        insumos_data = [
            # Papelería básica
            ('INS001', 'Resma de Papel A4 (500 hojas)'),
            ('INS002', 'Resma de Papel Oficio (500 hojas)'),
            ('INS003', 'Papel Membretado Institucional'),
            ('INS004', 'Sobres Oficio'),
            ('INS005', 'Sobres Manila A4'),
            ('INS006', 'Carpetas Colgantes'),
            ('INS007', 'Carpetas con Gancho'),
            ('INS008', 'Biblioratos'),
            ('INS009', 'Separadores de Archivo'),
            ('INS010', 'Etiquetas Adhesivas'),
            
            # Útiles de escritorio
            ('INS011', 'Bolígrafo Azul'),
            ('INS012', 'Bolígrafo Negro'),
            ('INS013', 'Bolígrafo Rojo'),
            ('INS014', 'Lápices HB'),
            ('INS015', 'Marcadores Permanentes Negro'),
            ('INS016', 'Marcadores Permanentes de Colores'),
            ('INS017', 'Resaltadores Amarillos'),
            ('INS018', 'Resaltadores Variados'),
            ('INS019', 'Corrector Líquido'),
            ('INS020', 'Gomas de Borrar'),
            
            # Material de oficina
            ('INS021', 'Clips N°1'),
            ('INS022', 'Clips N°3'),
            ('INS023', 'Ganchos Mariposa'),
            ('INS024', 'Broches para Carpeta'),
            ('INS025', 'Grapas 26/6'),
            ('INS026', 'Grapadora Estándar'),
            ('INS027', 'Grapadora Industrial'),
            ('INS028', 'Sacagrapas'),
            ('INS029', 'Perforadora 2 Agujeros'),
            ('INS030', 'Tijeras de Oficina'),
            
            # Adhesivos
            ('INS031', 'Cinta Adhesiva Transparente'),
            ('INS032', 'Cinta de Embalar'),
            ('INS033', 'Cinta de Papel'),
            ('INS034', 'Notas Adhesivas 75x75mm'),
            ('INS035', 'Notas Adhesivas 50x40mm'),
            ('INS036', 'Pegamento en Barra'),
            ('INS037', 'Voligoma 250ml'),
            
            # Tecnología
            ('INS038', 'Toner HP Negro'),
            ('INS039', 'Toner HP Color'),
            ('INS040', 'Cartucho de Tinta Negro'),
            ('INS041', 'Cartucho de Tinta Color'),
            ('INS042', 'Pilas AA'),
            ('INS043', 'Pilas AAA'),
            ('INS044', 'Pendrives 16GB'),
            ('INS045', 'CD-R'),
            ('INS046', 'DVD-R'),
            
            # Limpieza y varios
            ('INS047', 'Alcohol en Gel'),
            ('INS048', 'Toallas de Papel'),
            ('INS049', 'Papel Higiénico'),
            ('INS050', 'Vasos Descartables'),
        ]
        
        insumos = []
        print("Generando stock inicial y entradas...")
        for cod, desc in insumos_data:
            # Stock inicial variado según tipo de insumo
            if 'Toner' in desc or 'Cartucho' in desc or 'Pendrive' in desc:
                stock_inicial = random.randint(10, 30)
            elif 'Papel' in desc or 'Resma' in desc:
                stock_inicial = random.randint(100, 300)
            else:
                stock_inicial = random.randint(50, 200)
            
            insumo = Insumo(
                codigo_insumo=cod,
                descripcion=desc,
                existencias_iniciales_anio=stock_inicial,  # Lo que tenías al inicio del año
                cantidad_entradas=0,  # ← CORRECCIÓN: Empezar en 0
                cantidad_salidas=0,
                stock_actual=stock_inicial,
                porcentaje_utilizado=0.0
            )
            db.session.add(insumo)
            db.session.flush()
            
            # Simular 2-5 entradas durante el año
            num_entradas = random.randint(2, 5)
            for j in range(num_entradas):
                if 'Toner' in desc or 'Cartucho' in desc:
                    cantidad_entrada = random.randint(5, 15)
                elif 'Papel' in desc or 'Resma' in desc:
                    cantidad_entrada = random.randint(20, 100)
                else:
                    cantidad_entrada = random.randint(10, 50)
                
                entrada = EntradaInsumo(
                    id_proveedor=random.choice(proveedores).id_proveedor,
                    cantidad=cantidad_entrada,
                    id_insumo=insumo.id,
                    fecha_entrada=datetime.now() - timedelta(days=random.randint(30, 150))
                )
                db.session.add(entrada)
                
                # Actualizar el insumo con la nueva entrada
                insumo.stock_actual += cantidad_entrada
                insumo.cantidad_entradas += cantidad_entrada
            
            insumos.append(insumo)

        db.session.commit()

        print("Generando 100+ solicitudes y entregas...")
        # Solicitudes y entregas (simulando 6 meses de actividad)
        todos_usuarios = admins + usuarios
        observaciones_posibles = [
            'Entrega completa',
            'Entrega urgente',
            'Para uso administrativo',
            'Reposición de stock',
            'Solicitado por Director',
            'Stock insuficiente, entrega parcial',
            'Última unidad disponible',
            'Requerido para evento institucional',
            ''
        ]
        
        num_solicitudes = 120
        for i in range(num_solicitudes):
            # Fecha aleatoria en los últimos 6 meses
            dias_atras = random.randint(0, 180)
            fecha_solicitud = datetime.now() - timedelta(days=dias_atras)
            
            usuario = random.choice(todos_usuarios)
            solicitud = SolicitudInsumo(
                id_usuario=usuario.id_usuario,
                estado=False,
                fecha_solicitud=fecha_solicitud
            )
            db.session.add(solicitud)
            db.session.flush()
            
            # Cada solicitud tiene entre 1 y 8 insumos
            num_insumos = random.randint(1, 8)
            insumos_solicitados = random.sample(insumos, num_insumos)
            detalles = []
            
            for insumo in insumos_solicitados:
                # Cantidad solicitada varía según el insumo
                if 'Papel' in insumo.descripcion or 'Resma' in insumo.descripcion:
                    cantidad = random.randint(2, 15)
                elif 'Toner' in insumo.descripcion or 'Cartucho' in insumo.descripcion:
                    cantidad = random.randint(1, 3)
                else:
                    cantidad = random.randint(1, 10)
                
                detalle = SolicitudDetalle(
                    id_solicitud=solicitud.id_solicitud,
                    id_insumo=insumo.id,
                    cantidad_solicitada=cantidad
                )
                db.session.add(detalle)
                detalles.append((detalle, insumo, cantidad))
            db.session.commit()
            
            # 85% de las solicitudes son entregadas (totalmente o parcialmente)
            if random.random() < 0.85:
                fecha_entrega = fecha_solicitud + timedelta(days=random.randint(1, 7))
                for detalle, insumo, cantidad in detalles:
                    # Determinar cantidad a entregar
                    if insumo.stock_actual >= cantidad:
                        cantidad_entregar = cantidad  # Entrega completa
                    elif insumo.stock_actual > 0:
                        cantidad_entregar = min(insumo.stock_actual, random.randint(1, cantidad))  # Entrega parcial
                    else:
                        cantidad_entregar = 0  # Sin stock
                    
                    if cantidad_entregar > 0:
                        salida = SalidaInsumo(
                            cantidad_entregada=cantidad_entregar,
                            id_usuario=usuario.id_usuario,
                            id_insumo=insumo.id,
                            id_solicitudes_insumos=detalle.id_solicitudes_insumos,
                            observaciones=random.choice(observaciones_posibles),
                            fecha_salida=fecha_entrega
                        )
                        db.session.add(salida)
                        
                        # Actualizar stock
                        insumo.stock_actual -= cantidad_entregar
                        insumo.cantidad_salidas += cantidad_entregar
                        total_inicial = insumo.existencias_iniciales_anio + insumo.cantidad_entradas
                        if total_inicial > 0:
                            insumo.porcentaje_utilizado = (insumo.cantidad_salidas / total_inicial) * 100
                
                # Marcar solicitud como completada si todos los detalles tienen salida
                if all(len(d.salidas) > 0 for d in solicitud.detalles):
                    solicitud.estado = True
            
            db.session.commit()
            
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{num_solicitudes} solicitudes procesadas...")

        print("\n✅ Base de datos poblada exitosamente con:")
        print(f"  - {len(admins)} administradores")
        print(f"  - {len(usuarios)} usuarios")
        print(f"  - {len(deps)} dependencias")
        print(f"  - {len(insumos)} tipos de insumos")
        print(f"  - {num_solicitudes} solicitudes")
        print(f"\n🔑 Credenciales:")
        print(f"  Admin: cedula=1000, contraseña=admin")
        print(f"  Usuario: cedula=2000, contraseña=usuario")

if __name__ == '__main__':
    seed_data()