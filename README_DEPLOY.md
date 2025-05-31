# Despliegue en Google Cloud Compute Engine e2-micro

## Guía completa para desplegar ColorPlastic en Compute Engine Free Tier

### Prerrequisitos

1. **Cuenta de Google Cloud** con facturación habilitada
2. **Instancia e2-micro** creada en Compute Engine
3. **Código fuente** subido a un repositorio Git (GitHub, GitLab, etc.)

### Paso 1: Crear la instancia de Compute Engine

```bash
# Crear instancia e2-micro (Free Tier)
gcloud compute instances create colorplastic-server \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --network-tier=PREMIUM \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=YOUR_SERVICE_ACCOUNT \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --boot-disk-device-name=colorplastic-server
```

### Paso 2: Configurar reglas de firewall

```bash
# Permitir tráfico HTTP y HTTPS
gcloud compute firewall-rules create allow-http-https \
    --allow tcp:80,tcp:443 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTP and HTTPS traffic"
```

### Paso 3: Conectarse a la instancia

```bash
gcloud compute ssh colorplastic-server --zone=us-central1-a
```

### Paso 4: Configurar el servidor

Una vez conectado a la instancia, ejecutar:

```bash
# 1. Descargar el código del repositorio
git clone https://github.com/TU_USUARIO/colorplastic.git
cd colorplastic

# 2. Hacer ejecutables los scripts
chmod +x setup_server.sh
chmod +x deploy_app.sh
chmod +x configure_services.sh

# 3. Configurar el servidor (instalar dependencias)
./setup_server.sh

# 4. Desplegar la aplicación
./deploy_app.sh

# 5. Configurar servicios del sistema
./configure_services.sh
```

### Paso 5: Configurar tu dominio/IP

1. **Obtener IP externa:**
```bash
gcloud compute instances describe colorplastic-server \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

2. **Actualizar configuración de Nginx:**
```bash
# Editar archivo de configuración
sudo nano /etc/nginx/sites-available/colorplastic
# Cambiar YOUR_DOMAIN_OR_IP por tu IP externa
```

3. **Actualizar Django settings:**
```bash
# Editar settings.py y cambiar ALLOWED_HOSTS
sudo nano /opt/colorplastic/colorplastic/colorplastic_project/settings.py
# Cambiar '*' por tu IP externa: ['TU_IP_EXTERNA']
```

4. **Reiniciar servicios:**
```bash
sudo systemctl reload nginx
sudo supervisorctl restart colorplastic
```

### Paso 6: Configurar SSL (Opcional pero recomendado)

```bash
# Instalar certificado SSL gratuito con Let's Encrypt
sudo certbot --nginx -d tu-dominio.com
```

### Verificación del despliegue

1. **Verificar servicios:**
```bash
sudo systemctl status nginx
sudo supervisorctl status colorplastic
```

2. **Ver logs:**
```bash
sudo tail -f /var/log/colorplastic.log
sudo tail -f /var/log/nginx/error.log
```

3. **Acceder a la aplicación:**
- Abrir navegador en: `http://TU_IP_EXTERNA`
- Admin: `http://TU_IP_EXTERNA/admin` (usuario: admin, contraseña: admin123)

### Comandos útiles para mantenimiento

```bash
# Actualizar código
cd /opt/colorplastic/colorplastic
sudo -u colorplastic git pull origin main
sudo -u colorplastic /opt/colorplastic/venv/bin/pip install -r requirements.txt
sudo -u colorplastic /opt/colorplastic/venv/bin/python manage.py migrate
sudo -u colorplastic /opt/colorplastic/venv/bin/python manage.py collectstatic --noinput
sudo supervisorctl restart colorplastic

# Ver estado de servicios
sudo systemctl status nginx
sudo supervisorctl status

# Reiniciar servicios
sudo systemctl restart nginx
sudo supervisorctl restart colorplastic
```

### Consideraciones para e2-micro

- **RAM limitada (1GB):** Configurado con 2 workers de Gunicorn para optimizar memoria
- **CPU compartida:** Rendimiento variable según uso de otros usuarios
- **Almacenamiento:** 30GB incluidos en Free Tier
- **Tráfico:** 1GB salida gratis por mes

### Costos estimados (después del Free Tier)

- **e2-micro:** ~$5-7 USD/mes
- **Almacenamiento (30GB):** ~$1.20 USD/mes
- **IP externa estática:** ~$1.46 USD/mes
- **Total aproximado:** ~$7-10 USD/mes

### Troubleshooting

1. **Error 502 Bad Gateway:**
   - Verificar que Gunicorn esté corriendo: `sudo supervisorctl status colorplastic`
   - Verificar logs: `sudo tail -f /var/log/colorplastic.log`

2. **Error de conexión a base de datos:**
   - Verificar PostgreSQL: `sudo systemctl status postgresql`
   - Verificar usuario y permisos de BD

3. **Archivos estáticos no cargan:**
   - Ejecutar: `sudo -u colorplastic /opt/colorplastic/venv/bin/python manage.py collectstatic --noinput`
   - Verificar permisos en `/opt/colorplastic/colorplastic/static/`

### Backup y recuperación

```bash
# Backup de base de datos
sudo -u postgres pg_dump colorplastic > backup_$(date +%Y%m%d).sql

# Backup de archivos de media
tar -czf media_backup_$(date +%Y%m%d).tar.gz /opt/colorplastic/colorplastic/media/
```