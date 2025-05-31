#!/bin/bash

# Script de despliegue para ColorPlastic en Compute Engine
set -e

APP_DIR="/opt/colorplastic"
REPO_URL="https://github.com/tu-usuario/colorplastic.git"  # Cambia esto por tu repositorio
VENV_DIR="$APP_DIR/venv"
PROJECT_DIR="$APP_DIR/colorplastic"

echo "=== Desplegando ColorPlastic ==="

# Cambiar al usuario de la aplicación
sudo -u colorplastic bash << 'EOF'
cd /opt/colorplastic

# Clonar o actualizar código
if [ ! -d "colorplastic" ]; then
    echo "Clonando repositorio..."
    git clone $REPO_URL colorplastic
else
    echo "Actualizando código..."
    cd colorplastic
    git pull origin main
    cd ..
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual e instalar dependencias
source venv/bin/activate
cd colorplastic
pip install --upgrade pip
pip install -r requirements.txt

# Configurar variables de entorno para producción
export DJANGO_SETTINGS_MODULE=colorplastic_project.settings
export DATABASE_URL=postgresql://colorplastic:ColorPlastic2024!@localhost/colorplastic
export DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Ejecutar migraciones
python manage.py migrate

# Recopilar archivos estáticos
python manage.py collectstatic --noinput

# Crear superusuario si no existe
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@colorplastic.com', 'admin123')" | python manage.py shell

EOF

echo "=== Aplicación desplegada correctamente ==="