FROM centos:7

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y sudo wget python-pip rsyslog netcat gnupg python python-psutil python-requests python-jsonschema unixODBC-devel postgresql authd postgresql-odbc && \
    pip install xmlrunner

COPY odbcinst.ini /etc
ADD mysql-connector-odbc-5.2.7-linux-el6-x86-64bit.tar.gz /

COPY ../../entrypoint.sh /
ENTRYPOINT ["bash", "/entrypoint.sh"]
