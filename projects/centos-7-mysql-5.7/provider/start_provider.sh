#! /bin/bash

counter=0
#until pg_isready -h catalog.example.org -d ICAT -U irods -q
# Note: pg_isready is not provided by the postgresql client package on CentOS 7
until nc -z catalog.example.org 3306; do
    sleep 1
    ((counter += 1))
done
echo Postgres took approximately $counter seconds to fully start ...

# Set up iRODS if not already done
if [ ! -e /var/lib/irods/setup_complete ]
    then
        python /var/lib/irods/scripts/setup_irods.py < /irods_provider.input
fi

# run the server
su - irods -c "/var/lib/irods/irodsctl restart"

touch /var/lib/irods/setup_complete

# Keep container running if the test fails.
tail -f /dev/null
# Is this better? sleep 2147483647d

