def is_catalog_database_container(container):
    return 'icat' in container.name

def is_catalog_service_provider_container(container):
    return 'provider' in container.name
