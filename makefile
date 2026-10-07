.PHONY: setup run debug stop clean migration deploy logs status restart


COMPOSE=docker compose


SERVICES=\
	db_vm \
	redis_vm \
	gunicorn_vm \
	daphne_vm \
	celery_vm \
	celery_beat_vm \
	nginx_vm


setup:
	@chmod +x setup.sh
	@chmod +x init-letsencrypt.sh
	@chmod +x ssl-renew.sh
	@chmod +x auto_update.sh
	@chmod +x install-cron.sh
	@./setup.sh


run:
	$(COMPOSE) up -d
	$(COMPOSE) exec -T gunicorn_vm python manage.py collectstatic --noinput


debug:
	$(COMPOSE) up


stop:
	$(COMPOSE) down


restart:
	$(COMPOSE) restart


status:
	$(COMPOSE) ps


logs:
	$(COMPOSE) logs --tail=100 -f


migration:
	$(COMPOSE) up -d db_vm redis_vm

	$(COMPOSE) run --rm -T gunicorn_vm \
		python manage.py makemigrations --noinput

	$(COMPOSE) run --rm -T gunicorn_vm \
		python manage.py migrate --noinput

	$(COMPOSE) run --rm -T gunicorn_vm \
		python manage.py collectstatic --noinput


deploy:
	@./auto_update.sh


clean:
	$(COMPOSE) down -v --remove-orphans

	docker system prune -f

	find . \
		-path "*/migrations/*.py" \
		! -name "__init__.py" \
		-delete || true

	find . \
		-path "*/migrations/*.pyc" \
		-delete || true

	find . \
		-name "*.sqlite3" \
		-delete || true

	find . \
		-name "__pycache__" \
		-type d \
		-exec rm -rf {} + || true