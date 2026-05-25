.PHONY: pipeline test streamlit

pipeline:
	python3 scripts/run_pipeline.py

test:
	python3 -m unittest discover -s tests

streamlit:
	streamlit run streamlit_app.py
