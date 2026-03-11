.PHONY: setup run debug stop clean fix-docker-permissions migration deploy

# Variables
export DJANGO_SETTINGS_MODULE=iica_plataforma.settings
COMPOSE=docker compose
SERVICES=redis_vm db_vm gunicorn_vm daphne_vm celery_vm nginx_vm

setup: fix-docker-permissions
	@sudo chmod +x ./init-letsencrypt.sh
	@sudo mkdir -p /var/www/certbot
	@sudo chmod 755 /var/www/certbot

	@sudo mkdir -p ./letsencrypt/www
	@sudo chmod -R 755 ./letsencrypt/www

	@sudo mkdir -p letsencrypt/conf
	@sudo chmod -R 755 letsencrypt/conf
	@sudo mkdir -p letsencrypt/conf/live/
	@sudo chmod -R 755 letsencrypt/conf/live/

	@bash setup.sh


run:
	$(COMPOSE) up --no-build -d --no-recreate $(SERVICES)
	@if [ "$$MODE" = "production" ]; then \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi


debug:
	$(COMPOSE) up --no-build --no-recreate $(SERVICES)
	@if [ "$$MODE" = "production" ]; then \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi


migration:
	$(COMPOSE) up --no-build --no-recreate -d $(SERVICES)
	$(COMPOSE) exec -T gunicorn_vm python manage.py makemigrations
	$(COMPOSE) exec -T gunicorn_vm python manage.py migrate
	@if [ "$$MODE" = "production" ]; then \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi
	$(COMPOSE) down


deploy:
	@echo "========================================="
	@echo " DEPLOY ACTUALIZANDO DESDE GITHUB"
	@echo "========================================="

	@git pull origin main

	@echo ">>> Reconstruyendo contenedores..."
	$(COMPOSE) build

	@echo ">>> Levantando servicios..."
	$(COMPOSE) up -d $(SERVICES)

	@echo ">>> Aplicando migraciones..."
	$(COMPOSE) exec -T gunicorn_vm python manage.py migrate

	@echo ">>> Recolectando estáticos..."
	@if [ "$$MODE" = "production" ]; then \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi

	@echo ">>> Reiniciando servicios web..."
	$(COMPOSE) restart gunicorn_vm daphne_vm nginx_vm

	$(COMPOSE) up --no-build -d --no-recreate $(SERVICES)
	@if [ "$$MODE" = "production" ]; then \
		$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput; \
	fi

	@echo "========================================="
	@echo " DEPLOY COMPLETADO"
	@echo "========================================="


stop:
	$(COMPOSE) stop
	$(COMPOSE) down


clean:
	@echo "==============================================="
	@echo " LIMPIEZA TOTAL (Docker + Proyecto + SSL)"
	@echo "==============================================="

	@echo ">>> Deteniendo contenedores..."
	- sudo docker compose down -v --remove-orphans

	@echo ">>> Eliminando recursos Docker..."
	- sudo docker system prune -a --volumes -f

	@echo ">>> Eliminando redes huérfanas..."
	- sudo docker network prune -f

	@echo ">>> Eliminando volúmenes huérfanos..."
	- sudo docker volume prune -f

	@echo ">>> Limpieza migraciones Django..."
	find . -path "*/migrations/*.py" ! -name "__init__.py" -delete || true
	find . -path "*/migrations/*.pyc" -delete || true
	find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + || true

	@echo ">>> Eliminando bases sqlite..."
	find . -name "*.sqlite3" -delete || true

	@echo ">>> Limpieza caché Python..."
	find . -name "__pycache__" -type d -exec rm -rf {} + || true
	find . -name "*.pyc" -delete || true
	find . -name "*.pyo" -delete || true

	@echo ">>> Eliminando estáticos..."
	rm -rf iica_plataforma/staticfiles/* || true
	rm -rf iica_plataforma/media/profile_images/* || true

	@echo ">>> Eliminando documentación..."
	rm -rf docs/ || true

	@echo ">>> Eliminando certificados locales..."
	rm -rf letsencrypt/ || true

	@echo ">>> Eliminando nginx.conf..."
	rm -f nginx.conf || true

	@echo ">>> Eliminando dhparam.pem..."
	if [ -f /etc/ssl/certs/dhparam.pem ]; then \
		echo "   - Borrando /etc/ssl/certs/dhparam.pem"; \
		sudo rm -f /etc/ssl/certs/dhparam.pem; \
	fi

	@echo "==============================================="
	@echo " LIMPIEZA COMPLETA FINALIZADA"
	@echo "==============================================="


fix-docker-permissions:
	@sudo usermod -aG docker $$(whoami)
	@sudo chmod 666 /var/run/docker.sock