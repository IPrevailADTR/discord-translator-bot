lint:
	ruff check src/discord_trad_bot/
	ruff check src/discord_trad_bot/tests/

test:
	pytest 

coverage:
	coverage run -m pytest
	coverage report -m

 dev:
	python src/discord_trad_bot/main.py
