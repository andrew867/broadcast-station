FROM python:3.13-slim@sha256:cf50a4f6ac4f026458b08d5222023d700ac806410dff5e9ca8728fa44f2b850f AS mediamtx
WORKDIR /fetch
RUN python -c "import urllib.request,hashlib,tarfile; urllib.request.urlretrieve('https://github.com/bluenviron/mediamtx/releases/download/v1.21.2/mediamtx_v1.21.2_linux_amd64.tar.gz','mediamtx.tar.gz'); assert hashlib.sha256(open('mediamtx.tar.gz','rb').read()).hexdigest()=='121be6e00397e473a95d83c75f4fcd3819a6af3b0e1a50889cba43ab4fab6a27'; tarfile.open('mediamtx.tar.gz').extractall(filter='data')"
FROM python:3.13-slim@sha256:cf50a4f6ac4f026458b08d5222023d700ac806410dff5e9ca8728fa44f2b850f AS source
WORKDIR /source
COPY . .
RUN python tools/verify_release.py && python tools/package_source.py /source /tmp/station-source.tar.gz

FROM python:3.13-slim@sha256:cf50a4f6ac4f026458b08d5222023d700ac806410dff5e9ca8728fa44f2b850f
COPY deploy/debian.sources /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng nodejs iproute2 iputils-ping mesa-va-drivers intel-media-va-driver && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-linux-x86_64.lock .
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements-linux-x86_64.lock && pip check
COPY skycam ./skycam
COPY samples ./samples
COPY examples ./examples
COPY deploy ./deploy
COPY tools ./tools
COPY --from=mediamtx /fetch/mediamtx /usr/local/bin/mediamtx
COPY --from=mediamtx /fetch/LICENSE /usr/share/doc/mediamtx/LICENSE
COPY --from=source /tmp/station-source.tar.gz /app/source/station-source.tar.gz
ENV STATION_OFFLINE=1 SKYCAM_PLAYOUT=0
RUN mkdir -p /app/data && useradd --uid 10001 skycam && chown skycam /app/data
USER skycam
EXPOSE 8765
CMD ["python", "-m", "uvicorn", "skycam.app:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1", "--no-access-log"]
