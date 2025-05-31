#!/bin/bash

# Script de configuración para Compute Engine e2-micro
# Este script configura el servidor Ubuntu/Debian para ejecutar la aplicación Django

set -e

echo "=== Configurando servidor para ColorPlastic ==="

# Actualizar sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar dependencias del sistema
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    postgresql \
    postgresql-contrib \
    git \
    supervisor \
    ufw \
    certbot \
    python3-certbot-nginx

# Crear usuario para la aplicación
sudo useradd --system --shell /bin/bash --home /opt/colorplastic --create-home colorplastic

# Configurar PostgreSQL
sudo -u postgres createdb colorplastic
sudo -u postgres createuser colorplastic
sudo -u postgres psql -c "ALTER USER colorplastic WITH PASSWORD 'ColorPlastic2024!';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE colorplastic TO colorplastic;"

# Configurar firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

# Crear directorio para la aplicación
sudo mkdir -p /opt/colorplastic
sudo chown colorplastic:colorplastic /opt/colorplastic

echo "=== Configuración del servidor completada ==="
echo "Ahora ejecute deploy_app.sh para desplegar la aplicación"