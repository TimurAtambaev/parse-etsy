FROM python:3.9-slim

WORKDIR /app
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.in-project true

COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-root
# python будет в /app/.venv/bin/python для IDE

COPY . /app

ENTRYPOINT ["poetry", "run"]
CMD ["poetry", "run", "python", "etsy/manage.py", "runserver", "0:8000"]
