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
        """Grant all privileges on database to user.

        This method must be overridden.

        Arguments:
        database -- name of the database on which privileges are being granted
        username -- name of the user for whom privileges are being granted
        """
        raise NotImplementedError('method not implemented for database strategy')

    def drop_database(self, name):
        """Drop a database.

        This method must be overridden.

        Arguments:
        name -- name of the database to drop
        """
        raise NotImplementedError('method not implemented for database strategy')

    def drop_user(self, username):
        """Drop a user.

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
    def __init__(self, container):
        """Construct a postgres_database_setup_strategy.

        Arguments:
        container -- docker.client.container running the database
        """
        self.container = container

    def execute_psql_command(self, psql_cmd):
        """Execute a psql command as the postgres user.
        """
        cmd = 'psql -c \"{}\"'.format(psql_cmd)
        return execute.execute_command(self.container, cmd, user='postgres')

    def create_database(self, name):
        """Create a database.

        This method must be overridden.

        Arguments:
        name -- name of the database to create
        """
        return self.execute_psql_command(
            'create database \\\"{}\\\";'.format(name))

    def create_user(self, username, password):
        """Create a user for the database.

        This method must be overridden.

        Arguments:
        username -- name of the user to create
        password -- password for the new user
        """
        return self.execute_psql_command(
            'create user {0} with password \'{1}\';'.format(username, password))

    def grant_privileges(self, database, username):
        """Grant all privileges on database to user.

        This method must be overridden.

        Arguments:
        database -- name of the database on which privileges are being granted
        username -- name of the user for whom privileges are being granted
        """
        return self.execute_psql_command(
            'grant all privileges on database \\\"{0}\\\" to {1};'.format(database, username))

    def drop_database(self, name):
        """Drop a database.

        This method must be overridden.

        Arguments:
        name -- name of the database to drop
        """
        return self.execute_psql_command(
            'drop database \\\"{}\\\";'.format(name))

    def drop_user(self, username):
        """Drop a user.

        This method must be overridden.

        Arguments:
        username -- name of the user to drop
        """
        return self.execute_psql_command(
            'drop user {};'.format(username))

    def list_databases(self):
        """List databases."""
        return self.execute_psql_command('\l')

def make_strategy(database, container):
    suffix = '_database_setup_strategy'
    return eval(context.image_name(database) + suffix)(container)

def setup_catalog(docker_client,
                  project_name,
                  database_tag,
                  service_instance=1,
                  database_name='ICAT',
                  database_user='irods',
                  database_password='testpassword'):
    logging.warning('setting up catalog [{}]'.format(project_name))

    container_name = context.irods_catalog_database_container(project_name, service_instance)

    container = docker_client.containers.get(container_name)

    strat = make_strategy(database_tag, container)

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
