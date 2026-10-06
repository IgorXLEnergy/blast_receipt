.PHONY: up down logs test lint

up:
	@test -f .env || cp .env.example .env
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f receipt-lab

test:
	python3 -m unittest discover -s service/tests -p 'test_*.py' -v

lint:
	python3 -m compileall -q service/app service/tests
	@find laravel-adapter -name '*.php' -type f -print0 | xargs -0 -n1 php -l
