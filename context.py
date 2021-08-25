def is_catalog_database_container(container):
    return 'icat' in container.name

def is_catalog_service_provider_container(container):
    return 'provider' in container.name

def get_container_name_from_project(project_name, container_base_name, instance=1):
    return '_'.join([project_name, container_base_name, str(instance)])

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
