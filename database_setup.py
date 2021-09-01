# grown-up modules
import docker
import logging

# local modules
import context
import execute

class database_setup_strategy(object):
    """'Base class' for strategies for database setup.

    This class should not be instantiated directly.
    """
    def create_database(self, name):
        """Create a database.

        This method must be overridden.

        Arguments:
        name -- name of the database to create
        """
        raise NotImplementedError('method not implemented for database strategy')

    def create_user(self, username, password):
        """Create a user for the database.

        This method must be overridden.

        Arguments:
        username -- name of the user to create
        password -- password for the new user
        """
        raise NotImplementedError('method not implemented for database strategy')

    def grant_privileges(self, database, username):
        """Grant all privileges on database to user called `username`.

        This method must be overridden.

        Arguments:
        database -- name of the database on which privileges are being granted
        username -- name of the user for whom privileges are being granted
        """
        raise NotImplementedError('method not implemented for database strategy')

    def drop_database(self, name):
        """Drop a database called `name`.

        This method must be overridden.

        Arguments:
        name -- name of the database to drop
        """
        raise NotImplementedError('method not implemented for database strategy')

    def drop_user(self, username):
        """Drop a user named `username`.

        This method must be overridden.

        Arguments:
        username -- name of the user to drop
        """
        raise NotImplementedError('method not implemented for database strategy')

    def list_databases(self):
        """List databases.

        This method must be overridden.
        """
        raise NotImplementedError('method not implemented for database strategy')


class postgres_database_setup_strategy(database_setup_strategy):
    """Database setup strategy for postgres"""
    def __init__(self, container=None, root_password=None, port=None):
        """Construct a postgres_database_setup_strategy.

        Arguments:
        container -- docker.client.container running the database
        root_password -- password for the root database user
        port -- port on which the postgres server is listening (default: 5432)
        """
        self.container = container
        self.root_password = root_password if root_password else 'testpassword'
        self.port = port if port else 5432

    def execute_psql_command(self, psql_cmd):
        """Execute a psql command as the postgres user.

        Arguments:
        psql_cmd -- command to be passed to psql via --command
        """
        cmd = 'psql --port {0} --command \"{1}\"'.format(self.port, psql_cmd)
        return execute.execute_command(self.container, cmd, user='postgres')

    def create_database(self, name):
        """Create a database.

        Arguments:
        name -- name of the database to create
        """
        return self.execute_psql_command('create database \\\"{}\\\";'.format(name))

    def create_user(self, username, password):
        """Create a user for the database.

        Arguments:
        username -- name of the user to create
        password -- password for the new user
        """
        return self.execute_psql_command('create user {0} with password \'{1}\';'
            .format(username, password))

    def grant_privileges(self, database, username):
        """Grant all privileges on database to user called `username`.

        Arguments:
        database -- name of the database on which privileges are being granted
        username -- name of the user for whom privileges are being granted
        """
        return self.execute_psql_command('grant all privileges on database \\\"{0}\\\" to {1};'
            .format(database, username))

    def drop_database(self, name):
        """Drop a database called `name`.

        Arguments:
        name -- name of the database to drop
        """
        return self.execute_psql_command('drop database \\\"{}\\\";'.format(name))

    def drop_user(self, username):
        """Drop a user named `username`.

        Arguments:
        username -- name of the user to drop
        """
        return self.execute_psql_command('drop user {};'.format(username))

    def list_databases(self):
        """List databases."""
        return self.execute_psql_command('\l')


class mysql_database_setup_strategy(database_setup_strategy):
    """Database setup strategy for mysql"""
    def __init__(self, container=None, root_password=None, port=None):
        """Construct a mysql_database_setup_strategy.

        Arguments:
        container -- docker.client.container running the database
        root_password -- password for the root database user
        database_port -- port on which the postgres server is listening (default: 3306)
        """
        self.container = container
        self.root_password = root_password if root_password else 'testpassword'
        self.port = port if port else 3306

    def execute_mysql_command(self, mysql_cmd, user='root', password='testpassword'):
        """Execute a mysql command as the postgres user.

        Arguments:
        mysql_cmd -- the command to be passed to mysql via --execute
        """
        cmd = ('mysql --port {0} --user {1} --password={2} --execute \"{3}\"'
            .format(self.port, user, password, mysql_cmd))
        return execute.execute_command(self.container, cmd)

    def create_database(self, name):
        """Create a database.

        Arguments:
        name -- name of the database to create
        """
        return self.execute_mysql_command('CREATE DATABASE {};'.format(name))

    def create_user(self, username, password):
        """Create a user for the database.

        Arguments:
        username -- name of the user to create
        password -- password for the new user
        """
        return self.execute_mysql_command('CREATE USER \'{0}\'@\'{1}\' IDENTIFIED BY \'{2}\';'
            .format(username, 'localhost', password))

    def grant_privileges(self, database, username):
        """Grant all privileges on database to user called `username`.

        Arguments:
        database -- name of the database on which privileges are being granted
        username -- name of the user for whom privileges are being granted
        """
        return self.execute_mysql_command('GRANT ALL ON {0}.* to \'{1}\'@\'{2}\';'
            .format(database, username, 'localhost'))

    def drop_database(self, name):
        """Drop a database called `name`.

        Arguments:
        name -- name of the database to drop
        """
        return self.execute_mysql_command('DROP DATABASE {};'.format(name))

    def drop_user(self, username):
        """Drop a user named `username`.

        Arguments:
        username -- name of the user to drop
        """
        return self.execute_mysql_command('DROP USER {0}@{1};'.format(username, 'localhost'))

    def list_databases(self):
        """List databases."""
        return self.execute_mysql_command('SHOW DATABASES;')


def make_strategy(database_tag, container=None, database_port=None, root_password=None):
    """Make a database setup strategy for the given database type.

    Arguments:
    database_tag -- tag for the docker image of the database service
    container -- docker container running the database service
    database_port -- port on which the database service is listening
    database_root_password -- password the database root user
    """
    suffix = '_database_setup_strategy'
    return (eval(context.image_repo(database_tag) + suffix)
        (container, database_port, root_password)
    )

def setup_catalog(docker_client,
                  project_name,
                  database_tag,
                  database_port=None,
                  service_instance=1,
                  database_name='ICAT',
                  database_user='irods',
                  database_password='testpassword',
                  root_password=None):
    """Set up the iRODS catalog on the specified database service.

    Arguments:
    docker_client -- docker client for interacting with containers
    project_name -- name of the docker-compose project in which the database service is running
    database_tag -- docker image tag for the database service
    database_port -- the port on which the database service is listening
    service_instance -- service instance number for the database service being targeted
    database_name -- name of the iRODS database (for testing, this should be 'ICAT')
    database_user -- name of the iRODS database user (for testing, this should be 'irods')
    database_password -- password for the iRODS database user (for testing this should be
                         'testpassword')
    root_password -- password for the root database user
    """
    logging.warning('setting up catalog [{}]'.format(project_name))

    container_name = context.irods_catalog_database_container(project_name, service_instance)

    container = docker_client.containers.get(container_name)

    strat = make_strategy(database_tag, container, database_port, root_password)

    ec = strat.create_database(database_name)
    if ec is not 0:
        raise RuntimeError('failed to create database [{}]'.format(database_name))

    ec = strat.create_user(database_user, database_password)
    if ec is not 0:
        raise RuntimeError('failed to create user [{}]'.format(database_user))

    ec = strat.grant_privileges(database_name, database_user)
    if ec is not 0:
        raise RuntimeError('failed to grant privileges to user [{0}] on database [{1}]'.format(database_user, database_name))

    strat.list_databases()
