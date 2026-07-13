# SSL Setup con Let's Encrypt + Certbot

## Prerrequisitos

- Dominio público apuntando a la IP del servidor (ej: `vida.example.com`)
- Puertos 80 y 443 abiertos en el firewall
- Servidor nginx corriendo y accesible desde internet
- `certbot` instalado en el servidor

## Instalación de Certbot

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Arch Linux
sudo pacman -S certbot certbot-nginx

# Alpine
apk add certbot certbot-nginx
```

## Obtener el Certificado

El nginx corre dentro de Docker, así que usamos el modo `standalone` (no el plugin `--nginx`).
Necesita el puerto 80 libre: detené el stack un momento si ya está corriendo.

```bash
# Detener el frontend si está levantado (libera el puerto 80)
docker compose -f docker-compose.prod.yml down

# Emitir el certificado
sudo certbot certonly --standalone -d vida.example.com

# Volver a levantar con TLS
DOMAIN=vida.example.com docker compose -f docker-compose.prod.yml -f docker-compose.prod.tls.yml up --build -d
```

Certbot automáticamente:
1. Verifica la propiedad del dominio (HTTP-01 en el puerto 80)
2. Obtiene el certificado de Let's Encrypt
3. Lo guarda en `/etc/letsencrypt/live/vida.example.com/`
4. Programa la renovación automática vía systemd timer

## Verificar la Configuración

```bash
# Verificar que el certificado se cargó correctamente
sudo nginx -t

# Recargar nginx
sudo systemctl reload nginx

# Verificar el certificado
sudo certbot certificates
```

## Renovación Automática

Certbot instala un timer de systemd (o cron) que verifica la renovación dos veces al día:

```bash
# Verificar el timer
sudo systemctl status certbot.timer

# Probar renovación manual
sudo certbot renew --dry-run
```

Los certificados de Let's Encrypt expiran a los 90 días. La renovación automática renueva cualquier certificado que falten menos de 30 días para expirar.

## Archivos Generados

| Archivo | Propósito |
|---------|-----------|
| `/etc/letsencrypt/live/vida.example.com/fullchain.pem` | Certificado + cadena completa |
| `/etc/letsencrypt/live/vida.example.com/privkey.pem` | Clave privada |
| `/etc/letsencrypt/live/vida.example.com/chain.pem` | Cadena de certificados intermedios |

## Notas

- Los paths de certificados en `nginx.tls.conf` usan `/etc/letsencrypt/live/${DOMAIN}/` — el valor de `${DOMAIN}` se sustituye en el arranque desde la variable de entorno `DOMAIN` (definida en `.env`), no hay que editar el archivo
- El server block HTTP (puerto 80) redirige automáticamente a HTTPS vía 301
- Se usan exclusivamente TLS 1.2 y 1.3 con ciphers seguros
- HSTS está habilitado por 1 año (`max-age=31536000`)

## Troubleshooting

```bash
# Verificar que el puerto 80/443 están abiertos
sudo ss -tlnp | grep -E ':(80|443)'

# Ver logs de certbot
sudo journalctl -u certbot.service

# Forzar renovación
sudo certbot renew --force-renewal
```
