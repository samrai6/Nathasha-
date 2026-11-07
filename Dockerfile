FROM mysterysd/wzmlx:latest

WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KOYEB_DEPLOYMENT=true

COPY requirements.txt ./
# pymediainfo 6.0.1 (pulled in transitively) uses legacy setup.py metadata.
# Its setuptools_scm build hook imports vcs_versioning, so install that
# build-time dependency before resolving the full requirements list.
RUN pip3 install --upgrade setuptools wheel \
    && pip3 install --no-cache-dir vcs-versioning \
    && pip3 install --no-cache-dir -r requirements.txt

COPY . ./
RUN chmod 755 start.sh aria.sh

# Long-running Telegram worker; no HTTP port is required unless BASE_URL is set.
CMD ["bash", "start.sh"]
