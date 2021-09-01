# grown-up modules
import logging
import os
import textwrap

# local modules
import archive
import context
import execute

# This is used to map a database-platform combination to a driver and a function for configuration
platform_to_odbc_context = {
    'mysql:5.7': {
        'centos:7': {
            'driver': os.path.join(os.getcwd(),
                                   'projects',
                                   'base',
                                   'centos-7',
                                   'mysql-5.7',
                                   'mysql-connector-odbc-5.2.7-linux-el6-x86-64bit.tar.gz'),
            'configuration': 'configure_mysql_odbc_driver_centos_7_mysql_57'
        },
        'ubuntu:16.04': {
            'driver': os.path.join(os.getcwd(),
                                   'projects',
                                   'base',
                                   'ubuntu-16.04',
                                   'mysql-5.7',
                                   'mysql-connector-odbc-5.2.7-linux-glibc2.5-x86-64bit.tar.gz'),
            'configuration': 'configure_mysql_odbc_driver'
        },
        'ubuntu:18.04': {
            'driver': os.path.join(os.getcwd(),
                                   'projects',
                                   'base',
                                   'ubuntu-18.04',
                                   'mysql-5.7',
                                   'mysql-connector-odbc-5.2.7-linux-glibc2.5-x86-64bit.tar.gz'),
            'configuration': 'configure_mysql_odbc_driver'
        },
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


def get_odbc_driver_path(project_name):
    """Get ODBC driver path from the context map based on database and platform.

    Arguments:
    project_name -- name of the docker-compose project from which the map keys are derived
    """
    platform_tag = context.platform_image_repo_and_tag(project_name)
    database_tag = context.database_image_repo_and_tag(project_name)
    return (platform_to_odbc_context[context.image_repo_and_tag_string(database_tag)]
                                    [context.image_repo_and_tag_string(platform_tag)]
                                    ['driver'])


def make_mysql_odbcinst_ini(csp_container, container_odbc_driver_dir):
    """Generate content for the /etc/odbcinst.ini configuration file used by mysql.

    Arguments:
    csp_container -- container running iRODS catalog service provider using the ODBC driver
    container_odbc_driver_dir -- path in `csp_container` containing the ODBC driver directory
    """
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


def configure_mysql_odbc_driver(project_name, csp_container, path_to_odbc_driver):
    """Configure ODBC driver for mysql.

    Argument:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    path_to_odbc_driver -- path to local archive file containing the ODBC driver package
    """
    odbc_driver = odbc_driver_path if odbc_driver_path else get_odbc_driver_path(project_name)
    logging.info('looking for odbc driver [{}]'.format(odbc_driver))

    container_odbc_driver_dir = archive.copy_archive_to_container(csp_container,
                                                                  odbc_driver,
                                                                  extension='.tar.gz')

    make_mysql_odbcinst_ini(csp_container, container_odbc_driver_dir)

def configure_mysql_odbc_driver_centos_7_mysql_57(project_name, csp_container, path_to_odbc_driver):
    """Configure ODBC driver for mysql.

    Argument:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    path_to_odbc_driver -- path to local archive file containing the ODBC driver package
    """
    odbc_driver = odbc_driver_path if odbc_driver_path else get_odbc_driver_path(project_name)
    logging.info('looking for odbc driver [{}]'.format(odbc_driver))

    container_odbc_driver_dir = archive.copy_archive_to_container(csp_container,
                                                                  odbc_driver,
                                                                  extension='.tar.gz')

    make_mysql_odbcinst_ini(csp_container, container_odbc_driver_dir)

    # Instructions from https://dev.mysql.com/doc/connector-odbc/en/connector-odbc-installation-binary-unix-tarball.html
    # This is highly specific to this driver version and this platform
    # This is needed in order for the older MySQL ODBC connector to work (TODO: Verify)
    copy_odbc_drivers_to_known_locations = ('cp {0}/lib/* /usr/lib64 && cp {0}/bin/* /usr/bin'
                                            .format(container_odbc_driver_dir))
    link_new_odbc_drivers_to_old_drivers = textwrap.dedent('''
        ln -s /usr/lib64/libodbc.so.2.0.0 /usr/lib64/libodbc.so.1 &&
        ln -s /usr/lib64/libodbcinst.so.2.0.0 /usr/lib64/libodbcinst.so.1''')

    ec = execute.execute_command(csp_container, 'bash -c \'{}\''.format(copy_odbc_drivers_to_known_locations))
    if ec is not 0:
        raise RuntimeError('failed to copy odbc drivers ec=[{}] [{}]]'
            .format(ec, csp_container.name))

    ec = execute.execute_command(csp_container, 'bash -c \'{}\''.format(link_new_odbc_drivers_to_old_drivers))
    if ec is not 0:
        raise RuntimeError('failed to symlink newer mysql ODBC drivers ec=[{}] [{}]'
            .format(ec, csp_container.name))


def configure_odbc_driver(project_name, csp_container, path_to_odbc_driver=None):
    """Make an ODBC setup strategy for the given database type.

    Arguments:
    project_name -- name of the docker-compose project in which the server resides
    csp_container -- docker container on which the iRODS catalog service provider is running
    path_to_odbc_driver -- if specified, the ODBC driver will be sought here
    """
    database_tag = context.database_image_repo_and_tag(project_name)
    platform_tag = context.platform_image_repo_and_tag(project_name)

    func_name = (platform_to_odbc_context[context.image_repo_and_tag_string(database_tag)]
                                         [context.image_repo_and_tag_string(platform_tag)]
                                         ['configuration'])

    eval(func_name)(project_name, csp_container, path_to_odbc_driver)
