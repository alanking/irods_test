def project_name(container_name):
    return container_name.split('_')[0]

def service_name(container_name):
    return container_name.split('_')[1]

def service_instance(container_name):
    return container_name.split('_')[2]

def container_name(project_name, service_name, service_instance=1):
    return '_'.join([project_name, service_name, str(service_instance)])

def image_name_and_tag(image_tag):
    return image_tag.split(':')

def image_name(image_tag):
    return image_name_and_version(image_tag)[0]

def image_version(image_tag):
    return image_name_and_version(image_tag)[1]

def is_catalog_database_container(container):
    return service_name(container.name) == 'catalog'

def is_catalog_service_provider_container(container):
    return service_name(container.name) == 'irods-catalog-provider'

