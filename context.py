def is_catalog_database_container(container):
    return 'icat' in container.name

def is_catalog_service_provider_container(container):
    return 'provider' in container.name

def get_container_name_from_project(project_name, container_base_name, instance=1):
    return '_'.join([project_name, container_base_name, str(instance)])
