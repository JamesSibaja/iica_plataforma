#!/usr/bin/env python3

import argparse
from pathlib import Path


def generate(domain: str, mode: str, with_ssl: bool = False):
    production = mode == "production"

    if with_ssl and not production:
        raise ValueError("--with-ssl solo puede utilizarse en producción.")

    if production:
        if with_ssl:
            config = f"""
events {{
    worker_connections 1024;
    multi_accept on;
}}

http {{
    client_max_body_size 150G;

    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream django_app {{
        server gunicorn_vm:8765;
    }}

    upstream daphne_app {{
        server daphne_vm:8089;
    }}

    # Rechazar dominios no reconocidos.
    server {{
        listen 80 default_server;
        server_name _;
        return 444;
    }}

    # HTTP: permitir la validación ACME y redirigir a HTTPS.
    server {{
        listen 80;
        server_name {domain} www.{domain};

        location ^~ /.well-known/acme-challenge/ {{
            root /var/www/certbot;
            default_type text/plain;
            try_files $uri =404;
        }}

        location / {{
            return 301 https://$host$request_uri;
        }}
    }}

    # HTTPS: aplicación Django.
    server {{
        listen 443 ssl;
        http2 on;

        server_name {domain} www.{domain};

        ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;

        location ^~ /.well-known/acme-challenge/ {{
            root /var/www/certbot;
            default_type text/plain;
            try_files $uri =404;
        }}

        location /ws/ {{
            proxy_pass http://daphne_app;
            proxy_http_version 1.1;

            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
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

        location / {{
            proxy_pass http://django_app;
            proxy_http_version 1.1;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }}
    }}
}}
"""
        else:
            # Producción inicial: HTTP sin certificado.
            # Esta configuración permite que Let's Encrypt
            # valide el dominio antes de activar HTTPS.
            config = f"""
events {{
    worker_connections 1024;
    multi_accept on;
}}

http {{
    client_max_body_size 150G;

    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream django_app {{
        server gunicorn_vm:8765;
    }}

    upstream daphne_app {{
        server daphne_vm:8089;
    }}

    server {{
        listen 80 default_server;
        server_name _;
        return 444;
    }}

    server {{
        listen 80;
        server_name {domain} www.{domain};

        location ^~ /.well-known/acme-challenge/ {{
            root /var/www/certbot;
            default_type text/plain;
            try_files $uri =404;
        }}

        location /ws/ {{
            proxy_pass http://daphne_app;
            proxy_http_version 1.1;

            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}

        location /static/ {{
            alias /app/staticfiles/;
            access_log off;
        }}

        location /media/ {{
            alias /app/media/;
            access_log off;
        }}

        location / {{
            proxy_pass http://django_app;
            proxy_http_version 1.1;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
    }}
}}
"""
    else:
        config = """
events {
    worker_connections 1024;
    multi_accept on;
}

http {
    client_max_body_size 150G;

    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream django_app {
        server gunicorn_vm:8765;
    }

    upstream daphne_app {
        server daphne_vm:8089;
    }

    server {
        listen 80;
        server_name localhost 127.0.0.1;

        location /ws/ {
            proxy_pass http://daphne_app;
            proxy_http_version 1.1;

            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /static/ {
            alias /app/staticfiles/;
            access_log off;
        }

        location /media/ {
            alias /app/media/;
            access_log off;
        }

        location / {
            proxy_pass http://django_app;
            proxy_http_version 1.1;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""

    Path("nginx.conf").write_text(
        config.strip() + "\n",
        encoding="utf-8",
    )

    print(
        f"Configuración Nginx generada: "
        f"modo={mode}, dominio={domain}, ssl={with_ssl}"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "mode",
        choices=["production", "development"],
    )

    parser.add_argument("domain")

    parser.add_argument(
        "--with-ssl",
        action="store_true",
    )

    args = parser.parse_args()

    generate(
        domain=args.domain,
        mode=args.mode,
        with_ssl=args.with_ssl,
    )


if __name__ == "__main__":
    main()