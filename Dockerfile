FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py config.py db.py dal.py utils.py token.json models.py dump_db.py create_db.py worker.py ./
COPY csv ./csv

ENV TZ=Europe/Moscow

CMD ["python", "main.py"]
