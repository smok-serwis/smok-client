FROM python:3.8

RUN ls -l && apt-get update
RUN pip install git+https://www.github.com/smok-serwis/smok-client.git

WORKDIR /app

ADD skylab /app/skylab
ADD dev.crt /app/dev.crt
ADD key.crt /app/key.crt

CMD ["python", "-m", "skylab.client"]
