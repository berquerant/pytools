dev: check test

.PHONY: check
check:  # Run lints, format checks.
	@pipenv run tox -e black,isort,flake8,mypy,pydocstyle -p 2

.PHONY: test
test:  # Run tests.
	@pipenv run tox -e py310

.PHONY: fix
fix:  # Format py sources.
	@pipenv run black $(BLACK_TARGET)
	@pipenv run isort $(ISORT_TARGET)

.PHONY: requirements
requirements: Pipfile.lock  # Generate requirements.txt
	@pipenv requirements > requirements.txt

.PHONY: install-dev
install-dev: requirements.txt  # Install executable for development.
	@python setup.py develop

.PHONY: dist
dist: requirements.txt  ## Build sdist.
	@python setup.py sdist
