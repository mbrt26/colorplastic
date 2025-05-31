import os
import sys
import django

# Configure Django similar to other standalone tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
sys.path.append('/workspace/colorplastic')
django.setup()

from django.test import TestCase
import uuid
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User

from gestion.models import (
    Materiales, Bodegas, Terceros, Lotes,
    MovimientosInventario, Despacho, DetalleDespacho
)
from gestion import views
from gestion.views import DetalleDespachoFormSet, DespachoForm
from unittest.mock import patch

class DespachoFormsetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester", password="pass")
        self.material = Materiales.objects.create(nombre=f"MatX-{uuid.uuid4()}", tipo="ProductoTerminado")
        self.bodega = Bodegas.objects.create(nombre=f"B1-{uuid.uuid4()}")
        self.tercero = Terceros.objects.create(nombre=f"Cliente-{uuid.uuid4()}", tipo="Cliente")
        self.lote = Lotes.objects.create(
            numero_lote=f"L-{uuid.uuid4()}",
            id_material=self.material,
            cantidad_inicial=Decimal("10.00"),
            cantidad_actual=Decimal("10.00"),
            id_bodega_actual=self.bodega,
            activo=True,
        )
        self.despacho = Despacho.objects.create(
            numero_remision=f"D-{uuid.uuid4()}",
            tercero=self.tercero,
            direccion_entrega="Dir",
            estado="pendiente",
            observaciones="",
            usuario_creacion=self.user,
        )
        DetalleDespacho.objects.create(
            despacho=self.despacho,
            producto=self.lote,
            cantidad=Decimal("5.00"),
            bodega_origen=self.bodega,
        )

    def test_formset_allows_existing_details(self):
        data = {
            "detalles-TOTAL_FORMS": "0",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
        }
        formset = DetalleDespachoFormSet(data, instance=self.despacho)
        self.assertTrue(formset.is_valid())

    def test_inventory_deducted_once(self):
        form_data = {
            "numero_remision": self.despacho.numero_remision,
            "tercero": self.tercero.pk,
            "direccion_entrega": "Dir",
            "estado": "despachado",
            "observaciones": "",
        }
        detalle = self.despacho.detalles.first()
        formset_data = {
            "detalles-TOTAL_FORMS": "1",
            "detalles-INITIAL_FORMS": "1",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-id": str(detalle.pk),
            "detalles-0-producto": str(self.lote.pk),
            "detalles-0-cantidad": "5.00",
            "detalles-0-bodega_origen": str(self.bodega.pk),
        }
        form = DespachoForm(form_data, instance=self.despacho)
        formset = DetalleDespachoFormSet(formset_data, instance=self.despacho)
        estado_anterior = self.despacho.estado
        self.assertTrue(form.is_valid())
        self.assertTrue(formset.is_valid())
        with patch("gestion.views.procesar_movimiento_inventario") as mock_proc:
            # form.is_valid() mutates the instance, so use captured value
            with transaction.atomic():
                despacho = form.save(commit=False)
                if despacho.estado == "despachado" and not despacho.fecha_despacho:
                    despacho.fecha_despacho = timezone.now()
                despacho.save()
                formset.instance = despacho
                formset.save()
                if estado_anterior != "despachado" and despacho.estado == "despachado":
                    print('details count first', despacho.detalles.count())
                    for det in despacho.detalles.all():
                        views.procesar_movimiento_inventario(
                            tipo_movimiento="Venta",
                            lote=det.producto,
                            cantidad=det.cantidad,
                            bodega_origen=det.bodega_origen,
                            id_destino_tercero=despacho.tercero,
                            consecutivo_soporte=despacho.numero_remision,
                        )
            self.assertEqual(mock_proc.call_count, 1)

        with patch("gestion.views.procesar_movimiento_inventario") as mock_proc:
            estado_anterior = self.despacho.estado
            form = DespachoForm(form_data, instance=self.despacho)
            formset = DetalleDespachoFormSet(formset_data, instance=self.despacho)
            self.assertTrue(form.is_valid())
            self.assertTrue(formset.is_valid())
            with transaction.atomic():
                despacho = form.save(commit=False)
                if despacho.estado == "despachado" and not despacho.fecha_despacho:
                    despacho.fecha_despacho = timezone.now()
                despacho.save()
                formset.instance = despacho
                formset.save()
                if estado_anterior != "despachado" and despacho.estado == "despachado":
                    print('details count second', despacho.detalles.count())
                    for det in despacho.detalles.all():
                        views.procesar_movimiento_inventario(
                            tipo_movimiento="Venta",
                            lote=det.producto,
                            cantidad=det.cantidad,
                            bodega_origen=det.bodega_origen,
                            id_destino_tercero=despacho.tercero,
                            consecutivo_soporte=despacho.numero_remision,
                        )
            self.assertEqual(mock_proc.call_count, 0)
