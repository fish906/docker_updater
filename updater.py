import logging
import docker
import sys
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DockerUpdateChecker:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            sys.exit(1)
    
    def fetch_container_images(self) -> List[str]:
        container_images = []
        
        try:
            for container in self.client.containers.list():
                image_name = container.attrs['Config']['Image']
                container_name = container.name
                container_images.append({
                    'name': container_name,
                    'image': image_name
                })
                logger.info(f"Found container: {container_name} using {image_name}")
        except Exception as e:
            logger.error(f"Error fetching containers: {e}")
            
        return container_images
    
    def get_local_digest(self, image_name: str) -> str:
        try:
            local_image = self.client.images.get(image_name)
            digest = local_image.attrs.get("RepoDigests", [None])[0]
            return digest
        except Exception as e:
            logger.error(f"Error getting local digest for {image_name}: {e}")
            return None
    
    def get_remote_digest(self, image_name: str) -> str:
        try:
            registry_data = self.client.images.get_registry_data(image_name)
            if registry_data and registry_data.attrs.get("Descriptor"):
                digest = registry_data.attrs["Descriptor"].get("digest")
                if digest:
                    # Format to match RepoDigests format
                    repo = image_name.split(':')[0]
                    return f"{repo}@{digest}"
        except Exception as e:
            logger.warning(f"Could not fetch remote digest for {image_name}: {e}")
        
        return None
    
    def check_for_updates(self) -> Dict[str, List[Dict]]:
        containers = self.fetch_container_images()
        
        if not containers:
            logger.warning("No running containers found")
            return {'updates_available': [], 'up_to_date': []}
        
        updates_available = []
        up_to_date = []
        
        for container in containers:
            image_name = container['image']
            container_name = container['name']
            
            logger.info(f"Checking {container_name}...")
            
            local_digest = self.get_local_digest(image_name)
            remote_digest = self.get_remote_digest(image_name)
            
            if not local_digest or not remote_digest:
                logger.warning(f"Could not compare digests for {container_name}")
                continue
            
            if local_digest != remote_digest:
                logger.info(f"✓ Update available for {container_name} ({image_name})")
                updates_available.append({
                    'container': container_name,
                    'image': image_name,
                    'local_digest': local_digest,
                    'remote_digest': remote_digest
                })
            else:
                logger.info(f"✓ {container_name} is up to date")
                up_to_date.append({
                    'container': container_name,
                    'image': image_name
                })
        
        return {
            'updates_available': updates_available,
            'up_to_date': up_to_date
        }
    
    def print_summary(self, results: Dict):
        print("\n" + "="*60)
        print("DOCKER UPDATER SUMMARY")
        print("="*60)
        
        if results['updates_available']:
            print(f"\nUpdates Available ({len(results['updates_available'])}):")
            for item in results['updates_available']:
                print(f"  - {item['container']}: {item['image']}")
        
        if results['up_to_date']:
            print(f"\nUp to Date ({len(results['up_to_date'])}):")
            for item in results['up_to_date']:
                print(f"  - {item['container']}: {item['image']}")
        
        print("\n" + "="*60)

def main():
    logger.info("Starting Docker update checker...")
    
    checker = DockerUpdateChecker()
    results = checker.check_for_updates()
    checker.print_summary(results)
    
    if results['updates_available']:
        logger.info("Updates are available!")
        sys.exit(0)
    else:
        logger.info("All containers are up to date")
        sys.exit(0)


if __name__ == '__main__':
    main()