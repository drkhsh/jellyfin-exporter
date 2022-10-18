FROM python:alpine

EXPOSE 9027

COPY requirements.txt /requirements.txt
COPY jellyfin_exporter.py /jellyfin_exporter.py

RUN apk add --update --no-cache curl
RUN pip install -r /requirements.txt && rm -rf requirements.txt

HEALTHCHECK --interval=1m CMD /usr/bin/curl -f http://localhost:9027/ || exit 1

ENTRYPOINT ["python", "/jellyfin_exporter.py"]
