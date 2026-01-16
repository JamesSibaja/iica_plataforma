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
	sudo docker system prune -a
	docker compose down
	rm -rf docs/
	sudo docker system prune -a

fix-docker-permissions:
	@sudo usermod -aG docker $$(whoami)
	@sudo chmod 666 /var/run/docker.sock

# requirements:
# 	@if command -v python3 &>/dev/null; then \
# 		PYTHON_CMD=python3; \
# 	elif command -v python &>/dev/null; then \
# 		PYTHON_CMD=python; \
# 	else \
# 		echo "Python is not installed. Installing Python3..."; \
# 		sudo apt-get update; \
# 		sudo apt-get install -y python3; \
# 		PYTHON_CMD=python3; \
# 	fi; \
# 	if [ ! -d "iica_plataforma/venv" ]; then \
# 		sudo $$PYTHON_CMD -m venv iica_plataforma/venv; \
# 	fi; \
# 	. iica_plataforma/venv/bin/activate; \
# 	pip install --upgrade pip; \
# 	pip install -r requirements.txt