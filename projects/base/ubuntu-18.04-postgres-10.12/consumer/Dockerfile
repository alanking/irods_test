FROM ubuntu:18.04

RUN apt-get update && \
    apt-get install -y sudo wget lsb-release apt-transport-https netcat curl gnupg

COPY ../../entrypoint.sh /
ENTRYPOINT ["bash", "/entrypoint.sh"]
