run:
	dos2unix export.csv
	PYTHONPATH=. ./fk.py export.csv
