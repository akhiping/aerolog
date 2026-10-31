.PHONY: dev setup seed test demo clean

dev:
	bash scripts/dev.sh

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

seed:
	python seed.py

test:
	python -m pytest tests/ -v

demo:
	python demo/run_demo.py

clean:
	rm -f aerolog.db
	rm -rf .venv frontend/node_modules
