install:
	pip install -e .[dev]

test:
	pytest -q

docs:
	$(MAKE) -C docs html

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
