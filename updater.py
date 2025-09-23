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
    local_digest_list = []

    for image_name in container_images:
        local_image = client.images.get(image_name)
        local_digest = local_image.attrs.get("RepoDigests", [None])[0]
        local_digest_list.append(local_digest)

    return local_digest_list

def get_remote_digest():
    remote_digest_list = []

    try:
        for image_name in container_images:
            new_image = client.images.pull(image_name)
            new_digest = new_image.attrs.get("RepoDigests", [None])[0]
            remote_digest_list.append(new_digest)
        
    except Exception as e:
        print(e)

    return remote_digest_list
        

def check_for_update():
    for i in range(0, len(ld) - 1):
        if ld[i] == rd[i]:
            print(f'Image is up to date: {ld[i]}')

        else:
            print('Update is available...')

if __name__ == '__main__':
    container_images = fetch_container_images()
    ld = get_local_digest()
    rd = get_remote_digest()

    check_for_update()
