FROM centos:7

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y sudo wget python-pip rsyslog netcat gnupg python python-psutil python-requests python-jsonschema unixODBC-devel postgresql authd postgresql-odbc && \
    pip install xmlrunner


RUN rpm --import https://packages.irods.org/irods-signing-key.asc && \
    wget -qO - https://packages.irods.org/renci-irods.yum.repo | tee /etc/yum.repos.d/renci-irods.yum.repo && \
    yum update -y && \
    yum install -y irods-runtime irods-icommands irods-server irods-database-plugin-mysql

COPY odbcinst.ini /etc
ADD mysql-connector-odbc-5.2.7-linux-el6-x86-64bit.tar.gz /
COPY start_provider.sh irods_provider.input /
RUN chmod u+x /start_provider.sh
ENTRYPOINT ["./start_provider.sh"]
