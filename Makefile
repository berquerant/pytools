.PHONY: dev
dev:
	@pipenv run check
	@pipenv run test

.PHONY: fix
fix:  # Format py sources.
	@pipenv run black $(BLACK_TARGET)
	@pipenv run isort $(ISORT_TARGET)

.PHONY: install-dev
install-dev: requirements.txt  # Install executable for development.
	@python setup.py develop

.PHONY: dist
dist: requirements.txt  ## Build sdist.
	@python setup.py sdist
