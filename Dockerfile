FROM python:latest

RUN useradd invresearch

WORKDIR /home/invresearch

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql cryptography

COPY app app
COPY migrations migrations
COPY invresearch.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP invresearch.py

RUN chown -R invresearch:invresearch ./
USER invresearch

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
