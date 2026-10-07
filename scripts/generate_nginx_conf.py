#!/usr/bin/env python3

import argparse
from pathlib import Path


def generate(domain: str, production: bool):

    if production:

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


        location /.well-known/acme-challenge/ {{

            root /var/www/certbot;

        }}


        location / {{

            return 301 https://$host$request_uri;
        }}
    }}


    server {{

        listen 443 ssl;

        http2 on;

        server_name {domain} www.{domain};


        ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;

        ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;


        ssl_protocols TLSv1.2 TLSv1.3;

        ssl_prefer_server_ciphers on;


        location / {{

            proxy_pass http://django_app;

            proxy_http_version 1.1;

            proxy_set_header Host $host;

            proxy_set_header X-Real-IP $remote_addr;

            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            proxy_set_header X-Forwarded-Proto https;
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
    }}
}}
"""

    else:

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

        listen 80;

        server_name localhost 127.0.0.1;


        location / {{

            proxy_pass http://django_app;

            proxy_http_version 1.1;

            proxy_set_header Host $host;

            proxy_set_header X-Real-IP $remote_addr;

            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            proxy_set_header X-Forwarded-Proto $scheme;
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
    }}
}}
"""


    Path("nginx.conf").write_text(
        config.strip() + "\n",
        encoding="utf-8"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "mode",
        choices=["production", "development"]
    )

    parser.add_argument(
        "domain"
    )

    parser.add_argument(
        "--with-ssl",
        action="store_true"
    )

    args = parser.parse_args()


    production = (
        args.mode == "production"
        and args.with_ssl
    )


    generate(
        args.domain,
        production
    )


if __name__ == "__main__":
    main()