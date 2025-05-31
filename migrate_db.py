#!/usr/bin/env python
"""
Script para ejecutar migraciones de Django en App Engine
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colorplastic_project.settings')
    django.setup()
    
    # Ejecutar migraciones
    print("🔄 Ejecutando migraciones de Django...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    # Crear superusuario si no existe
    print("👤 Verificando superusuario...")
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@colorplastic.com', 'admin123')
        print("✅ Superusuario 'admin' creado con contraseña 'admin123'")
    else:
        print("✅ Superusuario ya existe")
    
    print("🎉 Migraciones completadas exitosamente!")