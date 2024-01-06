lint:
	.env/bin/pylint --disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,too-many-arguments $$(git ls-files '*.py')

black: sort
	.env/bin/black $$(git ls-files '*.py')

sort:
	.env/bin/isort $$(git ls-files '*.py')

clean:
	rm -rf feeds.sqlite*