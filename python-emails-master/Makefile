
clean:
	find . -name '*.pyc'  -exec rm -f {} \;
	find . -name '*.py~'  -exec rm -f {} \;
	find . -name '__pycache__'  -exec rm -rf {} \;
	find . -name '.coverage.*' -exec rm -rf {} \;
	rm -rf build dist emails.egg-info tmp-emails _files

test:
	tox

pypi:
	python setup.py sdist bdist_wheel upload
