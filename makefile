.PHONY: setup run debug stop clean fix-docker-permissions migration deploy enable-microsoft enable-storage

# =========================
# CARGAR VARIABLES
# =========================

-include .env
export $(shell [ -f .env ] && sed 's/=.*//' .env)

# =========================
# VARIABLES
# =========================

export DJANGO_SETTINGS_MODULE=iica_plataforma.settings
export DOCKER_BUILDKIT=0

COMPOSE=docker compose

SERVICES=redis_vm db_vm gunicorn_vm daphne_vm celery_vm celery_beat_vm nginx_vm


# =========================
# SETUP INICIAL
# =========================

setup: fix-docker-permissions

	@echo ">>> Preparando entorno e infraestructura..."

	@sudo chmod +x ./init-letsencrypt.sh
	@sudo chmod +x ./auto_update.sh

	@sudo mkdir -p /var/www/certbot
	@sudo mkdir -p ./letsencrypt/www
	@sudo mkdir -p ./letsencrypt/conf/live/

	@sudo chmod -R 755 /var/www/certbot ./letsencrypt/www ./letsencrypt/conf

	@bash setup.sh

	@echo ">>> Generando migraciones y recolectando estáticos..."

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py makemigrations --noinput

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py migrate website_management --noinput

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py migrate --noinput

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py collectstatic --noinput

	@echo ">>> Activando auto-restart de contenedores..."

	@docker update --restart unless-stopped $$(docker ps -q) || true

	@echo ""
	@echo "========================================="
	@echo " SETUP COMPLETADO"
	@echo "========================================="
	@echo ""


# =========================
# RUN & DEBUG
# =========================

run:

	$(COMPOSE) up --no-build -d --no-recreate $(SERVICES)

	@echo "Recolectando estáticos..."

	$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput


debug:

	$(COMPOSE) up --no-build --no-recreate $(SERVICES)


# =========================
# MIGRACIONES LOCALES
# =========================

migration:

	$(COMPOSE) up -d db_vm redis_vm

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py makemigrations --noinput

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py migrate website_management --noinput

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py migrate --noinput

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py collectstatic --noinput


# =========================
# DEPLOY DESDE GITHUB
# =========================

deploy:

	@echo "========================================="
	@echo " DEPLOY ACTUALIZANDO DESDE GITHUB"
	@echo "========================================="

	@echo ">>> Obteniendo cambios de GitHub..."

	@git fetch origin main

	@echo ">>> Sincronizando código con origin/main..."

	@git reset --hard origin/main

	@echo ">>> Reconstruyendo imágenes Docker..."

	$(COMPOSE) build

	@echo ">>> Levantando base de datos y Redis..."

	$(COMPOSE) up -d db_vm redis_vm

	@echo ">>> Esperando a PostgreSQL..."

	@until $(COMPOSE) exec -T db_vm pg_isready -U postgres > /dev/null 2>&1; do \
		echo "Esperando PostgreSQL..."; \
		sleep 2; \
	done

	@echo ">>> PostgreSQL listo."

	@echo ">>> Aplicando migraciones..."

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py migrate website_management --noinput

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py migrate --noinput

	@echo ">>> Recolectando estáticos..."

	$(COMPOSE) run --rm -T gunicorn_vm python manage.py collectstatic --noinput

	@echo ">>> Levantando todos los servicios..."

	$(COMPOSE) up -d $(SERVICES)

	@echo ">>> Configurando allauth automáticamente..."

	$(COMPOSE) exec -T gunicorn_vm python manage.py shell < scripts/setup_allauth.py || true

	@echo ">>> Activando auto-restart de contenedores..."

	@docker update --restart unless-stopped $$(docker ps -q) || true

	@echo "========================================="
	@echo " DEPLOY COMPLETADO"
	@echo "========================================="


# =========================
# ENABLE MICROSOFT AUTH
# =========================

enable-microsoft:

	@echo "========================================="
	@echo " ACTIVANDO AUTENTICACIÓN MICROSOFT"
	@echo "========================================="

	@read -p "Client ID: " cid; \
	read -p "Client Secret: " secret; \
	read -p "Tenant ID: " tid; \
	sed -i '/USE_MICROSOFT_AUTH/d' .env; \
	sed -i '/MICROSOFT_CLIENT_ID/d' .env; \
	sed -i '/MICROSOFT_CLIENT_SECRET/d' .env; \
	sed -i '/MICROSOFT_TENANT_ID/d' .env; \
	echo "USE_MICROSOFT_AUTH=True" >> .env; \
	echo "MICROSOFT_CLIENT_ID=$$cid" >> .env; \
	echo "MICROSOFT_CLIENT_SECRET=$$secret" >> .env; \
	echo "MICROSOFT_TENANT_ID=$$tid" >> .env; \
	$(COMPOSE) restart gunicorn_vm daphne_vm


# =========================
# ENABLE REMOTE STORAGE
# =========================

enable-storage:

	@echo "========================================="
	@echo " ACTIVANDO ALMACENAMIENTO REMOTO"
	@echo "========================================="

	@read -p "Access Key ID: " key; \
	read -p "Secret Access Key: " secret; \
	read -p "Bucket Name: " bucket; \
	read -p "Endpoint URL (dejar vacío para AWS S3): " endpoint; \
	read -p "Custom Domain (ej. cdn.tu-dominio.com): " domain; \
	sed -i '/USE_REMOTE_STORAGE/d' .env; \
	sed -i '/AWS_ACCESS_KEY_ID/d' .env; \
	sed -i '/AWS_SECRET_ACCESS_KEY/d' .env; \
	sed -i '/AWS_STORAGE_BUCKET_NAME/d' .env; \
	sed -i '/AWS_S3_ENDPOINT_URL/d' .env; \
	sed -i '/AWS_S3_CUSTOM_DOMAIN/d' .env; \
	echo "USE_REMOTE_STORAGE=True" >> .env; \
	echo "AWS_ACCESS_KEY_ID=$$key" >> .env; \
	echo "AWS_SECRET_ACCESS_KEY=$$secret" >> .env; \
	echo "AWS_STORAGE_BUCKET_NAME=$$bucket" >> .env; \
	echo "AWS_S3_ENDPOINT_URL=$$endpoint" >> .env; \
	echo "AWS_S3_CUSTOM_DOMAIN=$$domain" >> .env; \
	$(COMPOSE) restart gunicorn_vm daphne_vm


# =========================
# STOP
# =========================

stop:

	$(COMPOSE) down


# =========================
# CLEAN
# =========================

clean:

	@echo "==============================================="
	@echo " LIMPIEZA TOTAL (Docker + Proyecto + SSL)"
	@echo "==============================================="

	- sudo docker compose down -v --remove-orphans
	- sudo docker system prune -a --volumes -f

	find . -path "*/migrations/*.py" ! -name "__init__.py" -delete || true
	find . -path "*/migrations/*.pyc" -delete || true
	find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + || true

	find . -name "*.sqlite3" -delete || true
	find . -name "__pycache__" -type d -exec rm -rf {} + || true
	find . -name "*.pyc" -delete || true

	rm -rf staticfiles/* || true
	rm -rf media/* || true

	rm -rf letsencrypt/ || true
	rm -f nginx.conf || true


# =========================
# FIX DOCKER PERMISSIONS
# =========================

fix-docker-permissions:

	@sudo usermod -aG docker $$(whoami)

	@sudo chmod 666 /var/run/docker.sock