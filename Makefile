VIRTUALENV = $(shell which virtualenv)

venv:
	$(VIRTUALENV) venv

clean:
	rm -rf venv
	find . -name '*.pyc' | xargs rm || true

install: venv
	. venv/bin/activate; pip install --requirement requirements.txt

test-install:
	. venv/bin/activate; pip install --requirement test-requirements.txt

test:
	. venv/bin/activate; nosetests tests

serve: 
	. venv/bin/activate; python -m hamms
