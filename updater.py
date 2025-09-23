import logging
import docker
import re

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

client = docker.from_env()

def fetch_container_images():
    container_images = []

    for container in client.containers.list():
        image_name = container.attrs['Config']['Image']
        container_images.append(image_name)

    return container_images

def get_local_digest():
    container_images = fetch_container_images()

    for image_name in container_images:
        local_image = client.images.get(image_name)
        local_digest = local_image.attrs.get("RepoDigests", [None])[0]

        return local_digest

container_image = fetch_container_images()

def get_local_digest():
    local_digest_list = []

    logger.info('Extracting local digest...')
    for image_name in container_image:
        local_image = client.images.get(image_name)
        local_digest = local_image.attrs.get("RepoDigests", [None])[0]
        local_digest_list.append(local_digest)

    return local_digest_list
    
if __name__ == '__main__':
    fetch_container_images()
    check_for_update()