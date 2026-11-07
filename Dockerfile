FROM mysterysd/wzmlx:latest

WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip3 install --upgrade setuptools wheel \
    && pip3 install --no-cache-dir -r requirements.txt

COPY . ./
RUN chmod 755 start.sh aria.sh

# Long-running Telegram worker; no HTTP port is required unless BASE_URL is set.
CMD ["bash", "start.sh"]
