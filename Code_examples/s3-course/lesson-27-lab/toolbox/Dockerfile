FROM python:3.12-slim

ARG RC_VERSION=0.1.30
ARG TARGETARCH

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates tar procps \
 && rm -rf /var/lib/apt/lists/*

# rc — официальный CLI RustFS (https://github.com/rustfs/cli/releases)
RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
      amd64) cands="linux-amd64 linux-amd64-gnu" ;; \
      arm64) cands="linux-arm64 linux-arm64-gnu" ;; \
      *) echo "unsupported arch: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    for c in $cands; do \
      url="https://github.com/rustfs/cli/releases/download/v${RC_VERSION}/rustfs-cli-${c}-v${RC_VERSION}.tar.gz"; \
      if curl -fsSL "$url" -o /tmp/rc.tgz; then ok=1; break; fi; \
    done; \
    [ "${ok:-0}" = 1 ] || { echo "не удалось скачать rc ${RC_VERSION}" >&2; exit 1; }; \
    tar -xzf /tmp/rc.tgz -C /tmp; \
    install -m 0755 /tmp/rc /usr/local/bin/rc; \
    rm -f /tmp/rc.tgz /tmp/rc; \
    rc --version

RUN pip install --no-cache-dir awscli

# path-style: у RustFS в этом стенде нет виртуальных доменов бакетов
RUN mkdir -p /root/.aws \
 && printf '[default]\nregion = us-east-1\ns3 =\n    addressing_style = path\n' > /root/.aws/config

COPY bin/ /usr/local/bin/
RUN chmod +x /usr/local/bin/*

WORKDIR /work
CMD ["sleep", "infinity"]
