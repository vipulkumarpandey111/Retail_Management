FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements/prod.txt requirements/base.txt /tmp/requirements/
RUN pip install --no-cache-dir -r /tmp/requirements/prod.txt

COPY . /app

EXPOSE 8000

CMD ["gunicorn", "retailflow.wsgi:application", "--bind", "0.0.0.0:8000"]

