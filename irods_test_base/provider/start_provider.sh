#! /bin/bash

# Start the Postgres database.
counter=0
until pg_isready -h catalog.example.org -d ICAT -U irods -q
do
    sleep 1
    ((counter += 1))
done
echo Postgres took approximately $counter seconds to fully start ...

# Set up iRODS.
python /var/lib/irods/scripts/setup_irods.py < /irods_provider.input

# run the server
su - irods -c "/var/lib/irods/irodsctl restart"

# Keep container running if the test fails.
tail -f /dev/null
# Is this better? sleep 2147483647d

