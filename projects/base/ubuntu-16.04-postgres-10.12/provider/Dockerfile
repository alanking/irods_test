FROM ubuntu:16.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y sudo wget lsb-release apt-transport-https python-pip libfuse2 unixodbc rsyslog netcat gnupg && \
    pip install xmlrunner

COPY ../../entrypoint.sh /
ENTRYPOINT ["bash", "./entrypoint.sh"]
