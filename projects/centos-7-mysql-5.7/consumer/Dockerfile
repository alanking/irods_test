FROM centos:7

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y sudo wget python-pip rsyslog netcat gnupg python python-psutil python-requests python-jsonschema && \
    pip install xmlrunner

RUN rpm --import https://packages.irods.org/irods-signing-key.asc && \
    wget -qO - https://packages.irods.org/renci-irods.yum.repo | tee /etc/yum.repos.d/renci-irods.yum.repo && \
    yum update -y && \
    yum install -y irods-runtime irods-icommands irods-server

COPY entrypoint.sh setup.input /
ENTRYPOINT ["bash", "/entrypoint.sh"]
