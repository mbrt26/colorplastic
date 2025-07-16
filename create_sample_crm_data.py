#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from gestion.models import (
    Terceros, Cliente, Contacto, Oportunidad, InteraccionCliente
)

def create_sample_data():
    print("Creando datos de ejemplo para CRM...")
    
    # Obtener o crear usuario admin
    try:
        user = User.objects.get(username='admin')
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin', 'admin@colorplastic.com', 'admin123')
        print("Usuario admin creado")
    
    # Crear algunos clientes de ejemplo
    clientes_data = [
        {
            'nombre': 'Envases del Pacífico S.A.',
            'identificacion': '900123456-7',
            'tipo_cliente': 'corporativo',
            'industria': 'Envases y Empaques',
            'limite_credito': 50000000
        },
        {
            'nombre': 'Plásticos Industriales Ltda.',
            'identificacion': '800234567-8',
            'tipo_cliente': 'pyme',
            'industria': 'Manufactura de Plásticos',
            'limite_credito': 20000000
        },
        {
            'nombre': 'Distribuidora Nacional de Reciclaje',
            'identificacion': '890345678-9',
            'tipo_cliente': 'distribuidor',
            'industria': 'Reciclaje y Medio Ambiente',
            'limite_credito': 80000000
        }
    ]
    
    clientes_creados = []
    
    for data in clientes_data:
        # Crear o actualizar tercero
        tercero, _ = Terceros.objects.update_or_create(
            identificacion=data['identificacion'],
            defaults={
                'nombre': data['nombre'],
                'tipo': 'Cliente',
                'direccion': 'Calle Principal 123',
                'telefono': '555-0100',
                'email': f"contacto@{data['nombre'].lower().replace(' ', '').replace('.', '')}.com",
                'activo': True
            }
        )
        
        # Crear o actualizar cliente CRM
        cliente, created = Cliente.objects.update_or_create(
            tercero=tercero,
            defaults={
                'tipo_cliente': data['tipo_cliente'],
                'estado': 'activo',
                'limite_credito': data['limite_credito'],
                'dias_credito': 30,
                'industria': data['industria'],
                'usuario_asignado': user,
                'fecha_ultima_interaccion': timezone.now()
            }
        )
        clientes_creados.append(cliente)
        print(f"Cliente {'creado' if created else 'actualizado'}: {data['nombre']}")
    
    # Crear contactos para cada cliente
    contactos_nombres = [
        ('Juan', 'Pérez', 'Gerente General'),
        ('María', 'González', 'Jefe de Compras'),
        ('Carlos', 'Rodríguez', 'Coordinador de Producción')
    ]
    
    for cliente in clientes_creados:
        for i, (nombre, apellido, cargo) in enumerate(contactos_nombres[:2]):  # 2 contactos por cliente
            tipo_contacto = 'principal' if i == 0 else 'compras'
            Contacto.objects.update_or_create(
                cliente=cliente,
                nombre=nombre,
                apellido=apellido,
                defaults={
                    'cargo': cargo,
                    'tipo_contacto': tipo_contacto,
                    'email': f"{nombre.lower()}.{apellido.lower()}@{cliente.tercero.nombre.lower().replace(' ', '').replace('.', '')}.com",
                    'telefono': '555-0200',
                    'celular': '300-1234567',
                    'activo': True,
                    'usuario_creacion': user
                }
            )
    
    # Crear oportunidades
    oportunidades_data = [
        {
            'nombre': 'Suministro de Material Reciclado Q1 2025',
            'valor': 25000000,
            'probabilidad': 80,
            'etapa': 'negociacion'
        },
        {
            'nombre': 'Contrato Anual de Peletizado',
            'valor': 120000000,
            'probabilidad': 60,
            'etapa': 'propuesta'
        },
        {
            'nombre': 'Proyecto de Inyección de Envases',
            'valor': 45000000,
            'probabilidad': 30,
            'etapa': 'calificacion'
        },
        {
            'nombre': 'Venta de Material Molido Premium',
            'valor': 18000000,
            'probabilidad': 90,
            'etapa': 'cierre'
        }
    ]
    
    oportunidades_creadas = []
    for i, data in enumerate(oportunidades_data):
        cliente = clientes_creados[i % len(clientes_creados)]
        contacto = cliente.contactos.first()
        
        oportunidad, created = Oportunidad.objects.update_or_create(
            nombre=data['nombre'],
            cliente=cliente,
            defaults={
                'contacto': contacto,
                'descripcion': f"Oportunidad de negocio para {data['nombre']}. Cliente con alto potencial de crecimiento.",
                'etapa': data['etapa'],
                'prioridad': random.choice(['alta', 'media', 'baja']),
                'valor_estimado': data['valor'],
                'probabilidad': data['probabilidad'],
                'fecha_cierre_estimada': timezone.now().date() + timedelta(days=random.randint(15, 60)),
                'usuario_asignado': user
            }
        )
        oportunidades_creadas.append(oportunidad)
        print(f"Oportunidad {'creada' if created else 'actualizada'}: {data['nombre']}")
    
    # Crear interacciones de ejemplo
    tipos_interaccion = ['llamada', 'email', 'reunion', 'visita']
    asuntos = [
        'Seguimiento de cotización',
        'Presentación de propuesta',
        'Reunión de negociación',
        'Visita a planta',
        'Llamada de seguimiento',
        'Envío de especificaciones técnicas',
        'Aclaración de dudas',
        'Coordinación de entrega'
    ]
    
    for _ in range(20):  # Crear 20 interacciones
        cliente = random.choice(clientes_creados)
        contacto = random.choice(list(cliente.contactos.all()))
        tipo = random.choice(tipos_interaccion)
        asunto = random.choice(asuntos)
        
        # Fecha aleatoria en los últimos 30 días
        dias_atras = random.randint(0, 30)
        fecha_interaccion = timezone.now() - timedelta(days=dias_atras)
        
        # Algunas interacciones tienen oportunidad asociada
        oportunidad = None
        if random.random() > 0.5 and cliente.oportunidades.exists():
            oportunidad = random.choice(list(cliente.oportunidades.all()))
        
        # Algunas requieren seguimiento
        requiere_seguimiento = random.random() > 0.7
        fecha_seguimiento = None
        if requiere_seguimiento:
            fecha_seguimiento = (timezone.now() + timedelta(days=random.randint(1, 7))).date()
        
        InteraccionCliente.objects.create(
            cliente=cliente,
            contacto=contacto,
            oportunidad=oportunidad,
            tipo=tipo,
            asunto=asunto,
            descripcion=f"Interacción de tipo {tipo} con {contacto.nombre} {contacto.apellido} sobre {asunto.lower()}. "
                       f"Se acordaron los siguientes puntos importantes para el desarrollo del negocio.",
            fecha_interaccion=fecha_interaccion,
            requiere_seguimiento=requiere_seguimiento,
            fecha_seguimiento=fecha_seguimiento,
            usuario=user
        )
    
    print("\n¡Datos de ejemplo creados exitosamente!")
    print(f"- {len(clientes_creados)} clientes")
    print(f"- {Contacto.objects.count()} contactos")
    print(f"- {len(oportunidades_creadas)} oportunidades")
    print(f"- {InteraccionCliente.objects.count()} interacciones")

if __name__ == '__main__':
    create_sample_data()