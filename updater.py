import docker
import logging
import dotenv

logger = logging.getLogger(__name__)
client = docker.from_env()
logging.basicConfig(filename='updater.log', level=logging.INFO)

def fetch_images():
    container_id_list = []
    list_of_images = []

    for container in client.containers.list():
        container_id_list.append(container.id)
        

    for image in container_id_list:
        conti = client.containers.get(image)
        images = conti.attrs['Config']['Image']
        list_of_images.append(images)
    
    return container_id_list

def get_new_image_id():
    list_of_images = fetch_images()
    conti = client.containers.get(list_of_images[2])
    images = conti.id
    print(client.images.get_registry_data(images))
    print(images)


def delete_unused_images():
    image_prune = client.images.prune()
    print(image_prune)
    
if __name__ == '__main__':
    fetch_images()
    get_new_image_id()