def is_catalog_database_container(container):
    return 'icat' in container.name

def is_catalog_service_provider_container(container):
    return 'provider' in container.name

def container_name(project_name, container_base_name, instance=1):
    return '_'.join([project_name, container_base_name, str(instance)])

def project_name(platform_tag, database_tag):
    return '-'.join(platform_tag.split(':') + platform_tag.split(':'))
