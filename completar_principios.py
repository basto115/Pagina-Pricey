import re
import unicodedata
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from farmacia.models import Medicamento

def norm(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    return re.sub(r"[^a-z0-9]+", " ", s.encode("ascii", "ignore").decode()).strip()

activos = {}
for m in Medicamento.objects.exclude(principio_activo="").exclude(principio_activo__isnull=True):
    clave = norm(m.principio_activo)
    if len(clave) > 5 and clave != "hidroxido":
        activos[clave] = m.principio_activo.strip()

pendientes = Medicamento.objects.filter(principio_activo="") | Medicamento.objects.filter(principio_activo__isnull=True)
actualizaciones = []

for m in pendientes.distinct():
    texto = " " + norm(m.nombre) + " "
    encontrados = {a for a in activos if " " + a + " " in texto}
    if len(encontrados) == 1:
        clave = next(iter(encontrados))
        if clave != "d calcio":
            actualizaciones.append((m.pk, activos[clave]))

with transaction.atomic():
    for pk, activo in actualizaciones:
        Medicamento.objects.filter(pk=pk, principio_activo="").update(principio_activo=activo)

print("ACTUALIZADOS:", len(actualizaciones))
print("PENDIENTES:", Medicamento.objects.filter(principio_activo="").count() + Medicamento.objects.filter(principio_activo__isnull=True).count())
