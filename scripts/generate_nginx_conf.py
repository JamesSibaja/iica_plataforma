import sys
import os

def generate_nginx_conf(mode, domain, with_ssl=False):
    conf = """
events {
    worker_connections 1024;
    multi_accept on;
}

http {
    client_max_body_size 150G;
    proxy_read_timeout 600s;
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    upstream django_app {
        server gunicorn_vm:8765;
    }

    upstream daphne_app {
        server daphne_vm:8089;
    }

    # Server por defecto para IPs directas (bloquea accesos raros)
    server {
        listen 80 default_server;
        server_name _;
        return 444;
    }
"""

    if mode == "development":
        conf += """
    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://django_app;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection "";
        }

        location /ws/ {
            proxy_pass http://daphne_app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /static/ {
            alias /app/static/;
            access_log off;
            expires 30d;
        }

        location /media/ {
            alias /app/media/;
            access_log off;
        }
    }
"""
    elif mode == "production":
        conf += f"""
    server {{
        listen 80;
        server_name {domain};

        location /.well-known/acme-challenge/ {{
            root /var/www/certbot;
        }}

        location / {{
            return 301 https://$host$request_uri;
        }}
    }}

    server {{
        listen 443 ssl http2;
        server_name {domain};

        ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;

        location / {{
            proxy_pass http://django_app;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }}

        location /ws/ {{
            proxy_pass http://daphne_app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }}

        location /static/ {{
            alias /app/staticfiles/;
            access_log off;
            expires 30d;
        }}

        location /media/ {{
            alias /app/media/;
            access_log off;
        }}
    }}
"""

    conf += "\n}\n"

    with open("nginx.conf", "w") as f:
        f.write(conf)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_nginx_conf.py <mode> <domain> [--with-ssl]")
        sys.exit(1)

    mode = sys.argv[1]
    domain = sys.argv[2]
    with_ssl = "--with-ssl" in sys.argv

    generate_nginx_conf(mode, domain, with_ssl)