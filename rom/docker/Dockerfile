FROM josephred-rom-base:latest

COPY rom/scripts /opt/josephred/scripts
COPY rom/overrides /opt/josephred/overrides

WORKDIR /opt/pokefirered

RUN python3 /opt/josephred/scripts/apply_josephred.py /opt/pokefirered /opt/josephred/overrides \
    && make -j"$(nproc)"
