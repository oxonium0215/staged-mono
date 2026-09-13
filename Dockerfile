FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fontforge \
        python3 \
        python3-fontforge \
        python3-pip \
        ttfautohint \
        nodejs \
        npm \
        zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

COPY requirements.txt package.json* ./
RUN python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt \
    && if [ -f package.json ]; then npm install; fi

CMD ["bash", "-c", "chmod +x ./build_variants.sh && ./build_variants.sh"]
