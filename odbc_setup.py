# grown-up modules
import logging
import os

# local modules
import archive
import context
import execute

platform_to_driver_map = {
    'mysql:5.7': {
        'centos:7':     'mysql-connector-odbc-5.2.7-linux-el6-x86-64bit.tar.gz',
        'ubuntu:16.04': 'mysql-connector-odbc-5.2.7-linux-glibc2.5-x86-64bit.tar.gz',
        'ubuntu:18.04': 'mysql-connector-odbc-5.2.7-linux-glibc2.5-x86-64bit.tar.gz'
    }
}

def configure_postgres_odbc_driver(project_name, csp_container, path_to_odbc_driver):
    """Configure ODBC driver for postgres.

    Argument:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    path_to_odbc_driver -- path to local archive file containing the ODBC driver package
    """
    logging.debug('no ODBC driver setup required for postgres [{}]'.format(csp_container))

def configure_mysql_odbc_driver(project_name, csp_container, path_to_odbc_driver):
    """Configure ODBC driver for mysql.

    Argument:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    path_to_odbc_driver -- path to local archive file containing the ODBC driver package
    """
    import textwrap

    if not path_to_odbc_driver:
        platform_tag = context.platform_image_repo_and_tag(project_name)
        database_tag = context.database_image_repo_and_tag(project_name)
        filename = (platform_to_driver_map[context.image_repo_and_tag_string(database_tag)]
                                          [context.image_repo_and_tag_string(platform_tag)])
        path_to_odbc_driver = os.path.join(os.getcwd(),
                                           'projects',
                                           'base',
                                           '-'.join(platform_tag),
                                           '-'.join(database_tag),
                                           filename)
        logging.info('looking for odbc driver [{}]'.format(path_to_odbc_driver))

    container_odbc_driver_dir = archive.copy_archive_to_container(csp_container,
                                                                  path_to_odbc_driver,
                                                                  extension='.tar.gz')

    odbcinst_ini_path = os.path.join('/etc', 'odbcinst.ini')
    odbcinst_ini_contents = textwrap.dedent("""\
        [MySQL ANSI]
        Description = MySQL OCBC 5.2 ANSI Driver
        Driver = {0}/lib/libmyodbc5a.so

        [MySQL Unicode]
        Description = MySQL OCBC 5.2  Unicode Driver
        Driver = {0}/lib/libmyodbc5w.so""".format(container_odbc_driver_dir))

    cmd = 'bash -c \'echo "{0}" > {1}\''.format(odbcinst_ini_contents, odbcinst_ini_path)
    ec = execute.execute_command(csp_container, cmd)
    if ec is not 0:
        raise RuntimeError('failed to populate odbcinst.ini [ec=[{0}], container=[{1}]]'
            .format(ec, csp_container))

    execute.execute_command(csp_container, 'cat {}'.format(odbcinst_ini_path))

def configure_odbc_driver(project_name, csp_container, path_to_odbc_driver=None):
    """Make an ODBC setup strategy for the given database type.

    Arguments:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    """
    database_type = context.image_repo(context.database_image_repo_and_tag(project_name))
    return eval('configure_{}_odbc_driver'.format(database_type))(project_name, csp_container, path_to_odbc_driver)
