print("importando app desde app")
from app import app, db
print("importación exitosa")
from app.shared.models import Insumo, EntradaInsumo, SalidaInsumo
