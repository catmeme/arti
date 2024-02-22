FROM python:3.10-slim AS development

ARG APP_DIR="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_DIR}

COPY requirements.txt ${APP_DIR}/
RUN pip install --upgrade pip setuptools wheel

COPY .gitignore Makefile README.md entrypoint.sh pyproject.toml requirements-dev.txt ./
COPY assets assets
COPY src src

RUN python -m venv venv \
    && . venv/bin/activate \
    && make install \
    && pip install awslambdaric

ENTRYPOINT ["sh", "entrypoint.sh"]
CMD ["--help"]

FROM python:3.10-slim AS production

ARG APP_DIR="/app"

WORKDIR ${APP_DIR}

COPY --from=development ${APP_DIR} .

# Have to patch embedchain to make HOME_DIR /tmp to be writtable in Lambda
RUN sed -i 's#HOME_DIR = str(Path.home())#HOME_DIR = "/tmp"#g' \
        /app/venv/lib/python3.10/site-packages/embedchain/constants.py \
    && sed -i 's#HOME_DIR = str(Path.home())#HOME_DIR = "/tmp"#g' \
        /app/venv/lib/python3.10/site-packages/embedchain/telemetry/posthog.py

ENTRYPOINT [ "/app/venv/bin/python", "-m", "awslambdaric" ]
CMD [ "arti_ai.lambda_handler.handler" ]
