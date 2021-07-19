#! /bin/bash

counter=0
# Note: pg_isready is not provided by the postgresql client package on CentOS 7
# Replaces: until pg_isready -h catalog.example.org -d ICAT -U irods -q
until nc -z catalog.example.org 5432; do
    sleep 1
    ((counter += 1))
done
echo Postgres took approximately $counter seconds to fully start ...

# Set up iRODS if not already done
if [ ! -e /var/lib/irods/setup_complete ]
    then
        python /var/lib/irods/scripts/setup_irods.py < /setup.input

        # Make sure univMSS interface is configured for testing
        su - irods -c "cp /var/lib/irods/msiExecCmd_bin/univMSSInterface.sh.template /var/lib/irods/msiExecCmd_bin/univMSSInterface.sh"
        su - irods -c "sed -i \"s/template-//g\" /var/lib/irods/msiExecCmd_bin/univMSSInterface.sh"
        su - irods -c "chmod u+x /var/lib/irods/msiExecCmd_bin/univMSSInterface.sh"
        su - irods -c "/var/lib/irods/msiExecCmd_bin/univMSSInterface.sh"
        chown irods:irods /var/lib/irods/msiExecCmd_bin/univMSSInterface.sh
fi

# run the server
su - irods -c "/var/lib/irods/irodsctl restart"

touch /var/lib/irods/setup_complete

# Keep container running if the test fails.
tail -f /dev/null
# Is this better? sleep 2147483647d

