import logging
import docker
import sys
from typing import List, Dict, Set
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DockerUpdateChecker:
    def __init__(self, exclude_containers=None, exclude_images=None):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            sys.exit(1)

        self.exclude_containers = exclude_containers or set()
        self.exclude_images = exclude_images or set()

    def should_exclude(self, container_name: str, image_name: str) -> bool:
        if container_name in self.exclude_containers:
            logger.info(f"Excluding {container_name} (matched container name)")
            return True
        
        for exclude_pattern in self.exclude_images:
            if exclude_pattern in image_name:
                logger.info(f"Excluding {container_name} (matched image pattern: {exclude_pattern})")
                return True
            
        return False
    
    def fetch_container_images(self) -> List[Dict]:
        container_images = []
        
        try:
            for container in self.client.containers.list():
                image_name = container.attrs['Config']['Image']
                container_name = container.name

                if self.should_exclude(container_name, image_name):
                    continue

                container_images.append({
                    'name': container_name,
                    'image': image_name
                })
                logger.debug(f"Found container: {container_name} using {image_name}")
        
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
                    repo = image_name.split(':')[0]
                    return f"{repo}@{digest}"
                
        except Exception as e:
            logger.warning(f"Could not fetch remote digest for {image_name}: {e}")
        
        return None
    
    def check_for_updates(self) -> Dict[str, List[Dict]]:
        containers = self.fetch_container_images()
        
        if not containers:
            logger.warning("No running containers to check (all may be excluded)")
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
                logger.info(f"  Update available for {container_name} ({image_name})")
                updates_available.append({
                    'container': container_name,
                    'image': image_name,
                    'local_digest': local_digest,
                    'remote_digest': remote_digest
                })

            else:
                logger.info(f"  {container_name} is up to date")
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
        print("DOCKER UPDATE CHECK SUMMARY")
        print("="*60)

        if self.exclude_containers or self.exclude_images:
            print(f"\nExclusions:")
            if self.exclude_containers:
                print(f"  Containers: {', '.join(sorted(self.exclude_containers))}")
            if self.exclude_images:
                print(f"  Images: {', '.join(sorted(self.exclude_images))}")
        
        if results['updates_available']:
            print(f"\nUpdates Available ({len(results['updates_available'])}):")
            for item in results['updates_available']:
                print(f"  - {item['container']}: {item['image']}")
        
        if results['up_to_date']:
            print(f"\nUp to Date ({len(results['up_to_date'])}):")
            for item in results['up_to_date']:
                print(f"  - {item['container']}: {item['image']}")
        
        print("\n" + "="*60)


def load_env_file(env_path='.env') -> Dict[str, Set[str]]:
    exclude_containers = set()
    exclude_images = set()
    log_level = None

    if not Path(env_path).exists():
        logger.warning(f"No .env file found at {env_path}")
        return {
            'containers': exclude_containers,
            'images': exclude_images,
            'log_level': log_level
        }

    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    if key == 'EXCLUDE_CONTAINERS' and value:
                        exclude_containers.update(
                            item.strip() for item in value.split(',') if item.strip()
                        )
                    elif key == 'EXCLUDE_IMAGES' and value:
                        exclude_images.update(
                            item.strip() for item in value.split(',') if item.strip()
                        )
                    elif key == 'LOG_LEVEL' and value:
                        log_level = value.upper()
        
        if exclude_containers:
            logger.debug(f"Loaded {len(exclude_containers)} container exclusions from {env_path}")
        
        if exclude_images:
            logger.debug(f"Loaded {len(exclude_images)} image exclusions from {env_path}")

        if log_level:
            logger.debug(f"Log level set to {log_level} from {env_path}")
            
    except Exception as e:
        logger.error(f"Error reading .env file: {e}")
    
    return {
        'containers': exclude_containers,
        'images': exclude_images,
        'log_level': log_level
    }


def main():
    env_config = load_env_file('.env')

    if env_config['log_level']:
        level = getattr(logging, env_config['log_level'], logging.INFO)
        logging.getLogger().setLevel(level)
        logger.setLevel(level)

    logger.info("Starting Docker update checker...")

    exclude_containers = env_config['containers']
    exclude_images = env_config['images']

    if exclude_containers:
        logger.info(f"Excluding containers: {', '.join(sorted(exclude_containers))}")
    if exclude_images:
        logger.info(f"Excluding image patterns: {', '.join(sorted(exclude_images))}")
    
    checker = DockerUpdateChecker(
        exclude_containers=exclude_containers,
        exclude_images=exclude_images
    )
    
    results = checker.check_for_updates()
    checker.print_summary(results)
    
    if results['updates_available']:
        logger.info("Updates are available!")
    else:
        logger.info("All containers are up to date")


if __name__ == '__main__':
    main()