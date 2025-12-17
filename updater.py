import logging
import docker
import sys
from typing import List, Dict, Set
from pathlib import Path
from datetime import datetime
from croniter import croniter
import time

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
                    'id': container.id,
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
                    'container_id': container['id'],
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
    
    def update_containers(self, containers_to_update: List[Dict]) -> Dict[str, List[Dict]]:
        successful = []
        failed = []

        for container_info in containers_to_update:
            container_name = container_info['container']
            container_id = container_info['container_id']
            image_name = container_info['image']
            
            try:
                logger.info(f"Updating {container_name}...")
                container = self.client.containers.get(container_id)
            
                config = container.attrs['Config']
                host_config = container.attrs['HostConfig']
                network_settings = container.attrs['NetworkSettings']
                
                logger.info(f"  Pulling new image: {image_name}")
                self.client.images.pull(image_name)
                
                logger.info(f"  Stopping container: {container_name}")
                container.stop(timeout=10)
                
                logger.info(f"  Removing old container: {container_name}")
                container.remove()
                
                logger.info(f"  Recreating container: {container_name}")
                
                networks = {}
                if 'Networks' in network_settings:
                    for net_name, net_config in network_settings['Networks'].items():
                        if net_name != 'bridge' or len(network_settings['Networks']) == 1:
                            networks[net_name] = {}
                
                new_container = self.client.containers.create(
                    image=image_name,
                    name=container_name,
                    command=config.get('Cmd'),
                    environment=config.get('Env'),
                    volumes=host_config.get('Binds'),
                    ports=host_config.get('PortBindings'),
                    network=list(networks.keys())[0] if networks else None,
                    restart_policy=host_config.get('RestartPolicy'),
                    detach=True
                )
                
                logger.info(f"  Starting new container: {container_name}")
                new_container.start()
                
                if len(networks) > 1:
                    for net_name in list(networks.keys())[1:]:
                        network = self.client.networks.get(net_name)
                        network.connect(new_container)
                
                logger.info(f"  Successfully updated {container_name}")
                successful.append({
                    'container': container_name,
                    'image': image_name
                })
                
            except Exception as e:
                logger.error(f"  Failed to update {container_name}: {e}")
                failed.append({
                    'container': container_name,
                    'image': image_name,
                    'error': str(e)
                })
        
        return {
            'successful': successful,
            'failed': failed
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
    auto_update = False
    watchless_schedule = '0 0 * * *'

    if not Path(env_path).exists():
        logger.warning(f"No .env file found at {env_path}")
        return {
            'containers': exclude_containers,
            'images': exclude_images,
            'log_level': log_level,
            'auto_update': auto_update,
            'watchless_schedule': watchless_schedule
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

                    elif key == 'AUTO_UPDATE' and value:
                        auto_update = value.lower() in ('true')

                    elif key == 'WATCHLESS_SCHEDULE' and value:
                        watchless_schedule = value
        
        if exclude_containers:
            logger.debug(f"Loaded {len(exclude_containers)} container exclusions from {env_path}")
        
        if exclude_images:
            logger.debug(f"Loaded {len(exclude_images)} image exclusions from {env_path}")

        if log_level:
            logger.debug(f"Log level set to {log_level} from {env_path}")
        
        if auto_update:
            logger.info(f"Auto-update enabled from {env_path}")

        if watchless_schedule:
            logger.info(f'Watchless schedule set to {watchless_schedule}')

    except Exception as e:
        logger.error(f"Error reading .env file: {e}")
    
    return {
        'containers': exclude_containers,
        'images': exclude_images,
        'log_level': log_level,
        'auto_update': auto_update,
        'watchless_schedule': watchless_schedule
    }


def validate_cron_schedule(cron_expression: str) -> bool:
    try:
        croniter(cron_expression)
        return True
    
    except Exception as e:
        logger.error(f"Invalid cron expression '{cron_expression}': {e}")
        return False

def get_next_run_time(cron_expression: str) -> datetime:
    cron = croniter(cron_expression, datetime.now())
    return cron.get_next(datetime)

def run_update_check():
    print("\n" + "="*60)
    print(f"Running scheduled update check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Running Watchless once on startup")
    print("="*60 + "\n")
    
    try:
        env_config = load_env_file('.env')
        
        exclude_containers = env_config['containers']
        exclude_images = env_config['images']
        auto_update = env_config['auto_update']
        
        checker = DockerUpdateChecker(
            exclude_containers=exclude_containers,
            exclude_images=exclude_images
        )
        
        results = checker.check_for_updates()
        checker.print_summary(results)
        
        if auto_update and results['updates_available']:
            logger.info("\n" + "="*60)
            logger.info("AUTO_UPDATE enabled - Starting container updates...")
            logger.info("="*60 + "\n")
            
            update_results = checker.update_containers(results['updates_available'])
            
            print("\n" + "="*60)
            print("UPDATE SUMMARY")
            print("="*60)
            
            if update_results['successful']:
                print(f"\n✓ Successfully Updated ({len(update_results['successful'])}):")
                for item in update_results['successful']:
                    print(f"  - {item['container']}: {item['image']}")
            
            if update_results['failed']:
                print(f"\n✗ Failed Updates ({len(update_results['failed'])}):")
                for item in update_results['failed']:
                    print(f"  - {item['container']}: {item['error']}")
            
            print("\n" + "="*60)
            
            if update_results['failed']:
                logger.warning("Some container updates failed!")

            else:
                logger.info("All containers updated successfully!")
        
        elif results['updates_available']:
            logger.info("\nUpdates are available! Set AUTO_UPDATE=true in .env to automatically update containers.")

        else:
            logger.info("All containers are up to date")
            
    except Exception as e:
        logger.error(f"Error during scheduled update check: {e}")

def main():
    env_config = load_env_file('.env')

    if env_config['log_level']:
        level = getattr(logging, env_config['log_level'], logging.INFO)
        logging.getLogger().setLevel(level)
        logger.setLevel(level)

    logger.info("Starting Docker update checker...")

    exclude_containers = env_config['containers']
    exclude_images = env_config['images']
    auto_update = env_config['auto_update']
    watchless_schedule = env_config['watchless_schedule']

    if exclude_containers:
        logger.info(f"Excluding containers: {', '.join(sorted(exclude_containers))}")
    if exclude_images:
        logger.info(f"Excluding image patterns: {', '.join(sorted(exclude_images))}")

    if watchless_schedule:
        if not validate_cron_schedule(watchless_schedule):
            logger.error("Invalid cron schedule. Running once and exiting.")
            watchless_schedule = None

        else:
            logger.info("="*60)
            logger.info("SCHEDULED MODE (CRON)")
            logger.info("="*60)
            logger.info(f"Cron expression: {watchless_schedule}")
            
            next_run = get_next_run_time(watchless_schedule)
            logger.info(f"Next run scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*60 + "\n")
            
            last_run = None
            
            try:
                while True:
                    now = datetime.now()
                    
                    if last_run is None:
                        cron = croniter(watchless_schedule, now)
                        next_scheduled = cron.get_next(datetime)
                        
                        time_until_next = (next_scheduled - now).total_seconds()
                        if time_until_next <= 60:
                            run_update_check()
                            last_run = now
                            next_run = get_next_run_time(watchless_schedule)
                            logger.info(f"Next run scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")

                    else:
                        cron = croniter(watchless_schedule, last_run)
                        next_scheduled = cron.get_next(datetime)
                        
                        if now >= next_scheduled:
                            run_update_check()
                            last_run = now
                            next_run = get_next_run_time(watchless_schedule)
                            logger.info(f"Next run scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    time.sleep(30)
                    
            except KeyboardInterrupt:
                logger.info("\nScheduler stopped by user")
                sys.exit(0)

    if not watchless_schedule:
        checker = DockerUpdateChecker(
            exclude_containers=exclude_containers,
            exclude_images=exclude_images
        )
        
        results = checker.check_for_updates()
        checker.print_summary(results)
        
        if auto_update and results['updates_available']:
            logger.info("\n" + "="*60)
            logger.info("AUTO_UPDATE enabled - Starting container updates...")
            logger.info("="*60 + "\n")
            
            update_results = checker.update_containers(results['updates_available'])
            
            print("\n" + "="*60)
            print("UPDATE SUMMARY")
            print("="*60)
            
            if update_results['successful']:
                print(f"\n  Successfully Updated ({len(update_results['successful'])}):")
                for item in update_results['successful']:
                    print(f"  - {item['container']}: {item['image']}")
            
            if update_results['failed']:
                print(f"\n  Failed Updates ({len(update_results['failed'])}):")
                for item in update_results['failed']:
                    print(f"  - {item['container']}: {item['error']}")
            
            print("\n" + "="*60)
            
            if update_results['failed']:
                logger.warning("Some container updates failed!")
            else:
                logger.info("All containers updated successfully!")
        
        elif results['updates_available']:
            logger.info("\nUpdates are available! Set AUTO_UPDATE=true in .env to automatically update containers.")
        else:
            logger.info("All containers are up to date")

if __name__ == '__main__':
    main()