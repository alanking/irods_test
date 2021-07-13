FROM ubuntu:16.04

RUN apt-get update && \
    apt-get install -y sudo wget lsb-release apt-transport-https netcat curl gnupg

RUN wget -qO - https://packages.irods.org/irods-signing-key.asc | apt-key add -; \
    echo "deb [arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/renci-irods.list; \
    apt-get update && \
    apt-get install -y irods-runtime irods-icommands irods-server

COPY start_consumer.sh irods_consumer.input /
RUN chmod u+x /start_consumer.sh
ENTRYPOINT ["/start_consumer.sh"]
