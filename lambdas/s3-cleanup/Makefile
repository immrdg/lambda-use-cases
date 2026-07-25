.PHONY: test build clean

test:
	python3 -m unittest test_handler.py

build:
	zip -r lambda-function.zip handler.py

clean:
	rm -f lambda-function.zip
