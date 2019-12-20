FROM python:3
CMD ["python3", "-m", "flask", "run"]
ENV FLASK_DEBUG=1
ENV FLASK_APP=app.py
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY src .
ENV FLASK_DEBUG=1
