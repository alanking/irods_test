def irods_catalog_database_service():
    return 'catalog'

def irods_catalog_provider_service():
    return 'irods-catalog-provider'

def irods_catalog_consumer_service():
    return 'irods-catalog-consumer'

def project_name(container_name):
    return container_name.split('_')[0]

def service_name(container_name):
    return container_name.split('_')[1]

def service_instance(container_name):
    return container_name.split('_')[2]

def container_name(project_name, service_name, service_instance=1):
    return '_'.join([project_name, service_name, str(service_instance)])

def container_hostname(container):
    import docker
    return container.client.api.inspect_container(container.name)['Config']['Hostname']

def image_name_and_tag(image_tag):
    return image_tag.split(':')

def image_name(image_tag):
    return image_name_and_tag(image_tag)[0]

def image_tag(image_tag):
    return image_name_and_tag(image_tag)[1]

def irods_catalog_provider_container(project_name, service_instance=1):
    return container_name(project_name, irods_catalog_provider_service(), service_instance)

def irods_catalog_consumer_container(project_name, service_instance=1):
    return container_name(project_name, irods_catalog_consumer_service(), service_instance)

def irods_catalog_database_container(project_name, service_instance=1):
    return container_name(project_name, irods_catalog_database_service(), service_instance)

def is_catalog_database_container(container):
    return service_name(container.name) == irods_catalog_database_service()

def is_catalog_service_provider_container(container):
    return service_name(container.name) == irods_catalog_provider_service()

def platform_image_tag(project_name, delimiter='-'):
    """Derive and return OS platform image tag from structured docker-compose project name.

    Arguments:
    project_name -- a project name which contains the OS platform name and version as its
                    next-to-last two elements in a `delimiter`-delimited string (e.g.
                    my-project-platform-platformversion-postgres-10.12) NOTE: The platform name
                    and version are expected to match the docker image name and tag combination
                    such that they can be concatenated in a colon-delimited fashion and match
                    an existing docker image tag (e.g. platform:platformversion).
    delimiter -- optional parameter which changes the delimiter for the string to parse
    """
    return ':'.join(project_name.split(delimiter)[-4:-2])

def database_image_tag(project_name, delimiter='-'):
    """Derive and return database image tag from structured docker-compose project name.

    Arguments:
    project_name -- a project name which contains the database name and version as its final
                    two elements in a `delimiter`-delimited string (e.g.
                    my-project-ubuntu-18.04-database-databaseversion). NOTE: The database name
                    and version are expected to match the docker image name and tag combination
                    such that they can be concatenated in a colon-delimited fashion and match
                    an existing docker image tag (e.g. database:databaseversion).
    delimiter -- optional parameter which changes the delimiter for the string to parse
    """
    return ':'.join(project_name.split(delimiter)[-2:])
