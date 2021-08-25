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

