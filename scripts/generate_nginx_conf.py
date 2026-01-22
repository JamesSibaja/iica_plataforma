import sys
import os
import subprocess

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
"""

    # ======================
    # DEVELOPMENT
    # ======================
    if mode == 'development':
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
            proxy_redirect off;
        }

        location /ws/ {
            proxy_pass http://daphne_app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        location /static/ {
            root /app/;
            try_files $uri =404;
        }

        location /media/ {
            alias /app/media/;
        }
    }
"""

    # ======================
    # PRODUCTION
    # ======================
    elif mode == 'production':

        # --- HTTP SIEMPRE ACTIVO ---
        conf += f"""
    server {{
        listen 80;
        server_name {domain};

        location /.well-known/acme-challenge/ {{
            root /var/www/certbot;
        }}

        location / {{
            proxy_pass http://django_app;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection "";
            proxy_redirect off;
        }}
    }}
"""

        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"

        # --- SOLO CREAR SSL SI EL CERT EXISTE ---
        if with_ssl and os.path.exists(cert_path) and os.path.exists(key_path):

            dhparam_path = '/etc/ssl/certs/dhparam.pem'
            if not os.path.exists(dhparam_path):
                subprocess.run(
                    ['openssl', 'dhparam', '-out', dhparam_path, '2048'],
                    check=True
                )

            conf += f"""
    server {{
        listen 443 ssl;
        server_name {domain};

        ssl_certificate {cert_path};
        ssl_certificate_key {key_path};

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;
        ssl_dhparam /etc/ssl/certs/dhparam.pem;

        location / {{
            proxy_pass http://django_app;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header Connection "";
            proxy_redirect off;
        }}

        location /ws/ {{
            proxy_pass http://daphne_app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }}

        location /static/ {{
            alias /app/staticfiles/;
        }}

        location /media/ {{
            alias /app/media/;
        }}
    }}
"""

    conf += "\n}\n"

    with open('nginx.conf', 'w') as f:
        f.write(conf)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python generate_nginx_conf.py <mode> <domain> [--with-ssl]")
        sys.exit(1)

    mode = sys.argv[1]
    domain = sys.argv[2]
    with_ssl = '--with-ssl' in sys.argv

    generate_nginx_conf(mode, domain, with_ssl)
