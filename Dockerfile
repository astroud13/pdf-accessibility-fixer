
FROM python:3.11
RUN apt-get update && apt-get install -y tesseract-ocr ghostscript && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
