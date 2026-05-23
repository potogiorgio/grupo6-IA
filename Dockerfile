FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN mkdir -p outputs data/tei

CMD sh -c "python src/wait_grobid.py && python src/download_pdfs.py && python src/run_grobid.py"