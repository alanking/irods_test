FROM centos:7

RUN yum update && \
    yum install -y epel-release &&
    yum install -y sudo wget python-pip rsyslog netcat gnupg && \
    pip install xmlrunner

RUN rpm --import https://core-dev.irods.org/irods-core-dev-signing-key.asc && \
    wget -qO - https://core-dev.irods.org/renci-irods-core-dev.yum.repo | sudo tee /etc/yum.repos.d/renci-irods-core-dev.yum.repo && \
    yum update -y && \
    yum install -y irods-runtime irods-icommands irods-server

# Set command to execute when launching the container.
COPY start_consumer.sh irods_consumer.input /
RUN chmod u+x /start_consumer.sh
ENTRYPOINT ["/start_consumer.sh"]
