# grown-up modules
import logging
import os

# local modules
import archive
import context
import execute

def configure_postgres_odbc_driver(cproject_name, sp_container):
    """Configure ODBC driver for postgres.

    Argument:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    """
    logging.debug('no ODBC driver configuration for postgres [{}]'.format(csp_container))

def configure_mysl_odbc_driver(project_name, csp_container):
    """Configure ODBC driver for mysql.

    Argument:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    """
    platform_tag = context.platform_image_repo_and_tag(project_name)
    database_tag = context.database_image_repo_and_tag(project_name)
    path_to_odbc_driver = os.path.join(os.getcwd(), 'projects', 

def configure_odbc_driver(project_name, csp_container):
    """Make an ODBC setup strategy for the given database type.

    Arguments:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    """
    database_type = context.image_repo(context.database_image_repo_and_tag(project_name))
    return eval('configure_{}_odbc_driver'.format(database_type))(project_name, csp_container)
