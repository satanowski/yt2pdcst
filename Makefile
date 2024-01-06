lint:
	.env/bin/pylint --disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,too-many-arguments $$(git ls-files '*.py')
