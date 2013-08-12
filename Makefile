VIRTUALENV = $(shell which virtualenv)

venv:
	$(VIRTUALENV) venv

clean:
	rm -rf venv
	! find . -name '*.pyc' | xargs rm

install: venv
	. venv/bin/activate; pip install -r requirements.txt

serve: 
	. venv/bin/activate; python hamms.py
