"""
Script para poblar la base de datos con datos de prueba
Ejecutar desde la raíz: python seed_database.py
"""
from app.tests import seed_data

if __name__ == '__main__':
    print("=" * 60)
    print("🌱 Iniciando población de base de datos...")
    print("=" * 60)
    seed_data()
    print("=" * 60)
    print("✅ Proceso completado")
    print("=" * 60)