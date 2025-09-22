import docker
import logging
import dotenv

logger = logging.getLogger(__name__)
client = docker.from_env()

def app_logging():
    logging.basicConfig(filename='updater.log', level=logging.INFO)
    container = client.images.list()
    
    print(container)
    

if __name__ == '__main__':
    app_logging()