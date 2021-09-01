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
    """Return the name of the container as constructed by docker-compose.

    The passed in `project_name` will have dots (.) removed because docker-compose strips all
    dots from its project names. docker-compose container names are generated in three parts
    which are delimited by underscores, like this:
        project-name_service-name_service-instance-as-a-1-indexed-integer

    Arguments:
    project_name -- name of the docker-compose project (1)
    service_name -- name of the service in the docker-compose project (2)
    service_instance -- number of the instance of the service instance (3)
    """
    return '_'.join([project_name.replace('.', ''), service_name, str(service_instance)])


def container_hostname(container):
    return container.client.api.inspect_container(container.name)['Config']['Hostname']


def image_repo_and_tag_string(image_repo_and_tag):
    """Return the docker image repo and tag tuple as a string of the form `repo:tag`.

    If `image_repo_and_tag` is already a string, `image_repo_and_tag` is returned.

    Arguments:
    image_repo_and_tag -- a tuple containing the docker image repo and tag
    """
    if isinstance(image_tag, str):
        return image_repo_and_tag

    return ':'.join(image_repo_and_tag)


def image_repo_and_tag(image_repo_and_tag_string):
    """Split the docker image tag string into a list of docker image name and tag.

    Arguments:
    image_repo_and_tag_string -- a standard docker image tag string of the form `repo:tag`
    """
    if isinstance(image_repo_and_tag_string, list):
        return image_repo_and_tag_string

    return image_repo_and_tag_string.split(':')


def image_repo(image_repo_and_tag_string):
    """Return the name portion of a docker image tag string."""
    return image_repo_and_tag(image_repo_and_tag_string)[0]


def image_tag(image_repo_and_tag_string):
    """Return the tag portion of a docker image tag string."""
    return image_repo_and_tag(image_repo_and_tag_string)[1]


def irods_catalog_provider_container(project_name, service_instance=1):
    return container_name(project_name, irods_catalog_provider_service(), service_instance)


def irods_catalog_consumer_container(project_name, service_instance=1):
    return container_name(project_name, irods_catalog_consumer_service(), service_instance)


def irods_catalog_database_container(project_name, service_instance=1):
    return container_name(project_name, irods_catalog_database_service(), service_instance)


def is_catalog_database_container(container):
    return service_name(container.name) == irods_catalog_database_service()


def is_irods_catalog_provider_container(container):
    return service_name(container.name) == irods_catalog_provider_service()


def is_irods_catalog_consumer_container(container):
    return service_name(container.name) == irods_catalog_consumer_service()


def platform_image_repo_and_tag(project_name, delimiter='-'):
    """Derive and return OS platform image tag from structured docker-compose project name.

    NOTE: The platform name and version are expected to match the docker image name and tag
    combination such that they can be concatenated in a colon-delimited fashion and match an
    existing docker image tag (e.g. platform:platformversion).

    Arguments:
    project_name -- a project name which contains the OS platform name and version as its
                    next-to-last two elements in a `delimiter`-delimited string (e.g.
                    my-project-platform-platformversion-postgres-10.12)
    delimiter -- optional parameter which changes the delimiter for the project name to parse
    """
    return project_name.split(delimiter)[-4:-2]


def database_image_repo_and_tag(project_name, delimiter='-'):
    """Derive and return database image tag from structured docker-compose project name.

    NOTE: The database name and version are expected to match the docker image name and tag
    combination such that they can be concatenated in a colon-delimited fashion and match an
    existing docker image tag (e.g. database:databaseversion).

    Arguments:
    project_name -- a project name which contains the database name and version as its final
                    two elements in a `delimiter`-delimited string (e.g.
                    my-project-ubuntu-18.04-database-databaseversion).
    delimiter -- optional parameter which changes the delimiter for the project name to parse
    """
    return project_name.split(delimiter)[-2:]


def irods_catalog_consumer_containers(containers):
    """Return the provided list of containers with only iRODS catalog consumers."""
    return [c for c in containers if is_irods_catalog_consumer_container(c)]
