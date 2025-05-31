#!/bin/bash

# Script completo de configuración de servicios para Compute Engine
set -e

echo "=== Configurando servicios del sistema ==="

# Copiar configuración de Nginx
sudo cp /opt/colorplastic/colorplastic/nginx_colorplastic /etc/nginx/sites-available/colorplastic
sudo ln -sf /etc/nginx/sites-available/colorplastic /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Copiar configuración de Supervisor
sudo cp /opt/colorplastic/colorplastic/colorplastic.conf /etc/supervisor/conf.d/

# Configurar variables de entorno del sistema
sudo tee /etc/environment << EOF
COMPUTE_ENGINE=1
DJANGO_SETTINGS_MODULE=colorplastic_project.settings
DATABASE_URL=postgresql://colorplastic:ColorPlastic2024!@localhost/colorplastic
EOF

# Recargar configuraciones
sudo nginx -t
sudo systemctl reload nginx
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start colorplastic

# Verificar servicios
echo "=== Verificando servicios ==="
sudo systemctl status nginx
sudo supervisorctl status colorplastic

echo "=== Configuración completada ==="
echo "La aplicación debería estar disponible en http://YOUR_IP"