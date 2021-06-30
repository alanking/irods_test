#! /bin/bash

# Wait until the provider is up and accepting connections.
until nc -z icat.example.org 1247; do
    sleep 1
done

# Set up iRODS if not already done
if [ ! -e /var/lib/irods/setup_complete ]
    then
        python /var/lib/irods/scripts/setup_irods.py < /irods_consumer.input
fi

# start server
su - irods -c "/var/lib/irods/irodsctl restart"

touch /var/lib/irods/setup_complete

# Keep container running if the test fails.
tail -f /dev/null
# Is this better? sleep 2147483647d

