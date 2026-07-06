.PHONY: install run-mcp poll summary simulate test docker-build docker-up docker-down

install:
	pip install -r requirements.txt

run-mcp:
	python main.py mcp-server

poll:
	python main.py poll --source telegram

summary:
	python main.py summary --month $(MONTH) --year $(YEAR) --chat-id $(CHAT_ID)

simulate:
	python scripts/simulate_e2e.py

test:
	pytest -q

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
