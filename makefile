.PHONY: setup run clean fix-docker-permissions migration

# Variables de entorno
export DJANGO_SETTINGS_MODULE=iica_plataforma.settings

setup: fix-docker-permissions
	# Ejecutar script de configuración
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
	docker compose up --no-build -d --no-recreate redis_vm db_vm gunicorn_vm daphne_vm celery_vm nginx_vm
	if [ "$$MODE" = "production" ]; then \
		docker compose exec gunicorn_vm python manage.py collectstatic --noinput; \
	fi

debug:
	docker compose up --no-build --no-recreate redis_vm db_vm gunicorn_vm daphne_vm celery_vm nginx_vm
	if [ "$$MODE" = "production" ]; then \
		docker compose exec gunicorn_vm python manage.py collectstatic --noinput; \
	fi

migration:
	docker compose up --no-build --no-recreate -d redis_vm db_vm gunicorn_vm daphne_vm celery_vm nginx_vm
	docker compose exec gunicorn_vm python manage.py makemigrations
	docker compose exec gunicorn_vm python manage.py migrate
	if [ "$$MODE" = "production" ]; then \
		docker compose exec gunicorn_vm python manage.py collectstatic --noinput; \
	fi
	docker compose down

stop:
	docker compose stop
	docker compose down

clean:
	@echo "==============================================="
	@echo " LIMPIEZA TOTAL (Docker + Proyecto + SSL)"
	@echo "==============================================="

	@echo ">>> Deteniendo y eliminando contenedores..."
	- sudo docker compose down -v --remove-orphans

	@echo ">>> Eliminando TODOS los recursos Docker..."
	- sudo docker system prune -a --volumes -f

	@echo ">>> Eliminando redes Docker huérfanas..."
	- sudo docker network prune -f

	@echo ">>> Eliminando volúmenes Docker huérfanos..."
	- sudo docker volume prune -f

	@echo ">>> Limpieza de migraciones Django..."
	find . -path "*/migrations/*.py" ! -name "__init__.py" -delete || true
	find . -path "*/migrations/*.pyc" -delete || true
	find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + || true

	@echo ">>> Eliminando bases de datos locales..."
	find . -name "*.sqlite3" -delete || true

	@echo ">>> Limpieza de caché Python..."
	find . -name "__pycache__" -type d -exec rm -rf {} + || true
	find . -name "*.pyc" -delete || true
	find . -name "*.pyo" -delete || true

	@echo ">>> Eliminando estáticos y media..."
	rm -rf iica_plataforma/staticfiles/*|| true
	rm -rf iica_plataforma/media/profile_images/* || true

	@echo ">>> Eliminando documentación generada..."
	rm -rf docs/ || true

	@echo ">>> Eliminando certificados Let's Encrypt locales..."
	rm -rf letsencrypt/ || true

	@echo ">>> Eliminando nginx.conf generado..."
	rm -f nginx.conf || true

	@echo ">>> Eliminando dhparam.pem si fue creado por el proyecto..."
	if [ -f /etc/ssl/certs/dhparam.pem ]; then \
		echo "   - Borrando /etc/ssl/certs/dhparam.pem"; \
		sudo rm -f /etc/ssl/certs/dhparam.pem; \
	fi

	@echo "==============================================="
	@echo " LIMPIEZA COMPLETA FINALIZADA"
	@echo "==============================================="

deploy:
	git pull
	docker compose build
	docker compose up -d
	docker compose exec gunicorn_vm python manage.py migrate
	docker compose exec gunicorn_vm python manage.py collectstatic --noinput

fix-docker-permissions:
	@sudo usermod -aG docker $$(whoami)
	@sudo chmod 666 /var/run/docker.sock

