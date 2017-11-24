run:
	@dos2unix -q export.csv
	@PYTHONPATH=. ./fk.py export.csv
