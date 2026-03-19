.PHONY: setup run debug stop clean fix-docker-permissions migration deploy enable-microsoft

# =========================
# CARGAR VARIABLES
# =========================
-include .env
export $(shell [ -f .env ] && sed 's/=.*//' .env)

# =========================
# VARIABLES
# =========================
export DJANGO_SETTINGS_MODULE=iica_plataforma.settings
COMPOSE=docker compose
SERVICES=redis_vm db_vm gunicorn_vm daphne_vm celery_vm nginx_vm

# =========================
# SETUP INICIAL
# =========================
setup: fix-docker-permissions
	@echo ">>> Preparando entorno..."
	@sudo chmod +x ./init-letsencrypt.sh

	@sudo mkdir -p /var/www/certbot
	@sudo chmod 755 /var/www/certbot

	@sudo mkdir -p ./letsencrypt/www
	@sudo chmod -R 755 ./letsencrypt/www

	@sudo mkdir -p letsencrypt/conf/live/
	@sudo chmod -R 755 letsencrypt/conf

	@bash setup.sh

	@echo ">>> Activando auto-restart de contenedores..."
	@docker update --restart unless-stopped $$(docker ps -q) || true


# =========================
# RUN
# =========================
run:
	$(COMPOSE) up --no-build -d --no-recreate $(SERVICES)
	@if [ "$$MODE" = "production" ]; then \
		echo "Recolectando estáticos..."; \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi


debug:
	$(COMPOSE) up --no-build --no-recreate $(SERVICES)
	@if [ "$$MODE" = "production" ]; then \
		echo "Recolectando estáticos..."; \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi


# =========================
# MIGRACIONES
# =========================
migration:
	$(COMPOSE) up --no-build --no-recreate -d $(SERVICES)
	$(COMPOSE) exec -T gunicorn_vm python manage.py makemigrations
	$(COMPOSE) exec -T gunicorn_vm python manage.py migrate
	@if [ "$$MODE" = "production" ]; then \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi
	$(COMPOSE) down


# =========================
# DEPLOY DESDE GITHUB
# =========================
deploy:
	@echo "========================================="
	@echo " DEPLOY ACTUALIZANDO DESDE GITHUB"
	@echo "========================================="

	@git fetch origin
	@git reset --hard origin/main

	@echo ">>> Reconstruyendo contenedores..."
	$(COMPOSE) build

	@echo ">>> Levantando servicios..."
	$(COMPOSE) up -d $(SERVICES)

	@echo ">>> Aplicando migraciones..."
	$(COMPOSE) exec -T gunicorn_vm python manage.py migrate

	@if [ "$$MODE" = "production" ]; then \
		echo ">>> Recolectando estáticos..."; \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi

	@echo ">>> Configurando allauth automáticamente..."
	$(COMPOSE) exec -T gunicorn_vm python manage.py shell < scripts/setup_allauth.py || true

	@echo ">>> Reiniciando servicios web..."
	$(COMPOSE) restart gunicorn_vm daphne_vm nginx_vm

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
	sed -i '/USE_MICROSOFT_AUTH/d' .env; \
	sed -i '/MICROSOFT_CLIENT_ID/d' .env; \
	sed -i '/MICROSOFT_CLIENT_SECRET/d' .env; \
	echo "USE_MICROSOFT_AUTH=True" >> .env; \
	echo "MICROSOFT_CLIENT_ID=$$cid" >> .env; \
	echo "MICROSOFT_CLIENT_SECRET=$$secret" >> .env;

	@echo ">>> Aplicando configuración en Django..."
	$(COMPOSE) exec -T gunicorn_vm python manage.py shell < scripts/setup_allauth.py

	@echo ">>> Reiniciando servicios..."
	$(COMPOSE) restart

	@echo "========================================="
	@echo " MICROSOFT AUTH ACTIVADO"
	@echo "========================================="


# =========================
# STOP
# =========================
stop:
	$(COMPOSE) stop
	$(COMPOSE) down


# =========================
# CLEAN TOTAL
# =========================
clean:
	@echo "==============================================="
	@echo " LIMPIEZA TOTAL (Docker + Proyecto + SSL)"
	@echo "==============================================="

	@echo ">>> Deteniendo contenedores..."
	- sudo docker compose down -v --remove-orphans

	@echo ">>> Eliminando recursos Docker..."
	- sudo docker system prune -a --volumes -f

	@echo ">>> Eliminando redes..."
	- sudo docker network prune -f

	@echo ">>> Eliminando volúmenes..."
	- sudo docker volume prune -f

	@echo ">>> Limpieza Django..."
	find . -path "*/migrations/*.py" ! -name "__init__.py" -delete || true
	find . -path "*/migrations/*.pyc" -delete || true
	find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + || true

	@echo ">>> Eliminando DBs locales..."
	find . -name "*.sqlite3" -delete || true

	@echo ">>> Limpieza Python..."
	find . -name "__pycache__" -type d -exec rm -rf {} + || true
	find . -name "*.pyc" -delete || true

	@echo ">>> Eliminando estáticos..."
	rm -rf iica_plataforma/staticfiles/* || true
	rm -rf iica_plataforma/media/profile_images/* || true

	@echo ">>> Eliminando SSL..."
	rm -rf letsencrypt/ || true

	@echo ">>> Eliminando nginx.conf..."
	rm -f nginx.conf || true

	@echo ">>> Eliminando dhparam.pem..."
	if [ -f /etc/ssl/certs/dhparam.pem ]; then \
		sudo rm -f /etc/ssl/certs/dhparam.pem; \
	fi

	@echo "==============================================="
	@echo " LIMPIEZA COMPLETA FINALIZADA"
	@echo "==============================================="


# =========================
# FIX DOCKER
# =========================
fix-docker-permissions:
	@sudo usermod -aG docker $$(whoami)
	@sudo chmod 666 /var/run/docker.sock