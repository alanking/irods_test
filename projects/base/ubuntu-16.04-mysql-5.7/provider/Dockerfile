FROM ubuntu:16.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y sudo wget lsb-release apt-transport-https python-pip libfuse2 unixodbc rsyslog netcat gnupg && \
    pip install xmlrunner

COPY odbcinst.ini /etc
ADD mysql-connector-odbc-5.2.7-linux-glibc2.5-x86-64bit.tar.gz /
COPY ../../entrypoint.sh /
ENTRYPOINT ["bash", "/entrypoint.sh"]
