FROM python:3.10-slim as builder

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt


FROM python:3.10-slim

WORKDIR /app

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY alembic.ini .

COPY token.json .
COPY main.py db.py dal.py utils.py models.py dump_db.py create_db.py worker.py ./
COPY csv ./csv

CMD ["alembic", "upgrade", "head", "&&", "python", "main.py"]




