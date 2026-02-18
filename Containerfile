FROM fedora:40
ARG TARGETARCH
ENV VEGETA_VERSION=12.13.0
RUN dnf update -y && dnf install --setopt=install_weak_deps=False -y tar gzip && dnf clean all
RUN curl -L https://github.com/tsenart/vegeta/releases/download/v${VEGETA_VERSION}/vegeta_${VEGETA_VERSION}_linux_${TARGETARCH}.tar.gz -o vegeta.tar.gz && \
    tar xzf vegeta.tar.gz -C /usr/local/bin vegeta && \
    rm vegeta.tar.gz && \
    chmod +x /usr/local/bin/vegeta
WORKDIR /http-load
COPY run.sh run.sh
RUN chmod +x ./run.sh
ENTRYPOINT ["/bin/bash", "run.sh"]
