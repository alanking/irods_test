FROM ubuntu:16.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y sudo wget lsb-release apt-transport-https python-pip libfuse2 unixodbc rsyslog netcat gnupg && \
    pip install xmlrunner

RUN wget -qO - https://packages.irods.org/irods-signing-key.asc | apt-key add -; \
    echo "deb [arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/renci-irods.list; \
    apt-get update && \
    apt-get install -y irods-runtime irods-icommands irods-server irods-database-plugin-mysql

COPY odbcinst.ini /etc
ADD mysql-connector-odbc-5.2.7-linux-glibc2.5-x86-64bit.tar.gz /
COPY wait_for_database.py start_provider.sh irods_provider.input /
RUN chmod u+x /start_provider.sh
ENTRYPOINT ["./start_provider.sh"]
