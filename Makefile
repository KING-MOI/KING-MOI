.PHONY: svg offline test

svg:
	python3 scripts/gen_svg.py

offline:
	python3 scripts/gen_svg.py --offline

test:
	python3 -m unittest discover -s tests -v
