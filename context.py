def project_name(container_name):
    return container_name.split('_')[0]

def service_name(container_name):
    return container_name.split('_')[1]

def service_instance(container_name):
    return container_name.split('_')[2]

def is_catalog_database_container(container):
    return service_name(container.name) == 'catalog'

def is_catalog_service_provider_container(container):
    return service_name(container.name) == 'irods-catalog-provider'

def container_name(project_name, service_name, service_instance=1):
    return '_'.join([project_name, service_name, str(service_instance)])

def image_name_and_version(image_tag):
    return image_tag.split(':')

def database_name_and_version(database_image_tag):
    return image_name_and_version(database_image_tag)

def database_name(database_image_tag):
    return database_name_and_version(database_image_tag)[0]

def database_version(database_image_tag):
    return database_name_and_version(database_image_tag)[1]

def platform_name_and_version(platform_image_tag):
    return image_name_and_version(platform_image_tag)

def platform_name(platform_image_tag):
    return platform_name_and_version(platform_image_tag)[0]

def platform_version(platform_image_tag):
    return platform_name_and_version(platform_image_tag)[1]
