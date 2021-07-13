FROM centos:7

RUN yum update && \
    yum install -y epel-release &&
    yum install -y sudo wget apt-transport-https python-pip libfuse2 unixodbc rsyslog netcat gnupg && \
    pip install xmlrunner

RUN rpm --import https://core-dev.irods.org/irods-core-dev-signing-key.asc && \
    wget -qO - https://core-dev.irods.org/renci-irods-core-dev.yum.repo | sudo tee /etc/yum.repos.d/renci-irods-core-dev.yum.repo && \
    yum update -y && \
    yum install -y irods-runtime irods-icommands irods-server irods-database-plugin-postgres

# Set command to execute when launching the container.
COPY start_provider.sh irods_provider.input /
RUN chmod u+x /start_provider.sh
ENTRYPOINT ["./start_provider.sh"]
