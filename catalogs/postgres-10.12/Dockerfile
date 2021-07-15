FROM postgres:10.12

ARG postgres_password
ENV POSTGRES_PASSWORD ${postgres_password}

COPY postgres_init.sh /docker-entrypoint-initdb.d/
