# Watchless

A lightweight, automated Docker container update manager with multi-channel notifications.

## Overview

Watchless monitors your running Docker containers for image updates and can automatically update them on a schedule. It preserves container configurations, manages networks, and cleans up old images - all while keeping you informed through your preferred notification channels.

**Why does this project exist?**
I used Watchtower for updating all my Docker Containers. Unfortunately Watchtower had more and more problems, probably due to not being acitvely maintained anymore. At some point, I didn't want to put more time into fixing individual problems. So I had a little time on my hands and then wrote this script (in its basics).

## Features

- **Automatic Update Detection** - Compares local and remote image digests without pulling
- **Automated Updates** - Optional automatic container updates with configuration preservation
- **Flexible Scheduling** - Cron-based scheduling for automated checks
- **Smart Exclusions** - Exclude containers by name or image pattern
- **Image Cleanup** - Optional removal of old images after updates
- **Multi-Channel Notifications** - Email, ntfy, Gotify, MS Teams and Slack support
- **Configuration Preservation** - Maintains volumes, networks, ports, and environment variables

## Quick Start

### Using Docker Run

```bash
docker run -d \
  --name watchless \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e AUTO_UPDATE=true \
  -e WATCHLESS_SCHEDULE="0 3 * * *" \
  -e EXCLUDE_CONTAINERS=watchless \
  fish906/watchless:latest
```

### Using Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
services:
  watchless:
    image: fish906/watchless:latest
    container_name: watchless
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      # Basic settings
      - LOG_LEVEL=INFO
      - AUTO_UPDATE=false
      - WATCHLESS_SCHEDULE=0 0 * * * # every day at midnight
      - WATCHLESS_CLEAN=false
      
      # Exclusions (always exclude watchless itself!)
      - EXCLUDE_CONTAINERS=watchless
      - EXCLUDE_IMAGES=
      
      # Notifications
      - EMAIL_NOTIFICATION=false
      - NTFY_NOTIFICATION=false
      - GOTIFY_NOTIFICATION=false
      - MSTEAMS_NOTIFICATION=false
      - SLACK_NOTIFICATION=false
    restart: unless-stopped
```

Start Watchless:
```bash
docker-compose up -d
```

## Configuration

All configuration is done through environment variables passed to the container.

### Core Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `AUTO_UPDATE` | Enable automatic container updates | `false` | `true` |
| `WATCHLESS_SCHEDULE` | Cron schedule for checks | None (run once) | `0 3 * * *` |
| `WATCHLESS_CLEAN` | Remove old images after updates | `false` | `true` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG` |
| `EXCLUDE_CONTAINERS` | Comma-separated container names to exclude | None | `watchless,db` |
| `EXCLUDE_IMAGES` | Comma-separated image patterns to exclude | None | `postgres,mysql` |

> **Important**: Always exclude the Watchless container itself to prevent self-updates and future complications!

### Schedule Examples

The schedule uses standard cron format: `minute hour day month day_of_week`

```yaml
# Every day at 3 AM
- WATCHLESS_SCHEDULE=0 3 * * *

# Every Saturday at midnight
- WATCHLESS_SCHEDULE=0 0 * * 6

# Every 6 hours
- WATCHLESS_SCHEDULE=0 */6 * * *

# Every hour
- WATCHLESS_SCHEDULE=0 * * * *

# Weekdays at 6 AM (Monday-Friday)
- WATCHLESS_SCHEDULE=0 6 * * 1-5

# First day of every month at midnight
- WATCHLESS_SCHEDULE=0 0 1 * *

# If set to "false" or not set at a all, Watchless will run once and exit
- WATCHLESS_SCHEDULE=false
```

### Notification Configuration

#### Email

```yaml
environment:
  - EMAIL_NOTIFICATION=true
  - SMTP_SERVER_URL=smtp.mail.com
  - MAIL_SENDER=your-email@mail.com
  - SMTP_PASSWORD=your-app-password
  - MAIL_RECEIVER=recipient@example.com
```

#### Ntfy

```yaml
environment:
  - NTFY_NOTIFICATION=true
  - NTFY_URL=https://ntfy.sh/your-topic
  - NTFY_PRIORITY_LEVEL=default  # Options: min, low, default, high, urgent
```

#### Gotify

```yaml
environment:
  - GOTIFY_NOTIFICATION=true
  - GOTIFY_APPTOKEN=your-app-token
  - GOTIFY_URL=gotify.example.com
  - GOTIFY_PRIORITY_LEVEL=5  # Options: 0-10
```

#### MS Teams

```yaml
environment:
  - MSTEAMS_NOTIFICATION=true
  - MSTEAMS_URL=https://outlook.office.com/webhook/...
```

#### Slack

```yaml
environment:
  - SLACK_NOTIFICATION=true
  - SLACK_BOT_TOKEN=xoxb-your-token
  - SLACK_CHANNEL_ID=your-channel-id
```

## Complete Docker Compose Example

Full configuration with multiple notification channels:

```yaml
services:
  watchless:
    image: fish906/watchless:latest
    container_name: watchless
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
environment:
      # Core Settings
      - LOG_LEVEL=INFO # DEBUG, INFO, WARNING, ERROR
      - AUTO_UPDATE=false # set to true for automated pulling and updating
      - WATCHLESS_SCHEDULE=0 0 * * * # every day at midnight
      - WATCHLESS_CLEAN=false # set to true to remove old images after restarting
      
      # Exclusions
      - EXCLUDE_CONTAINERS=watchless,postgres-main,redis-cache # always exclude watchless itself
      - EXCLUDE_IMAGES=postgres:14,mysql:8 
      
      # Email Notifications
      - EMAIL_NOTIFICATION=true
      - SMTP_SERVER_URL=smtp.mail.com
      - MAIL_SENDER=watchless@example.com
      - SMTP_PASSWORD=your-app-password
      - MAIL_RECEIVER=admin@example.com
      
      # ntfy Notifications
      - NTFY_NOTIFICATION=true
      - NTFY_URL=https://ntfy.sh/example-url
      - NTFY_PRIORITY_LEVEL=default
      
      # Gotify Notifications
      - GOTIFY_NOTIFICATION=true
      - GOTIFY_APPTOKEN=
      - GOTIFY_URL=
      - GOTIFY_PRIORITY_LEVEL=5
      
      # MS Teams Notifications
      - MSTEAMS_NOTIFICATION=false
      - MSTEAMS_URL=
      
      # Slack Notifications
      - SLACK_NOTIFICATION=false
      - SLACK_BOT_TOKEN=
      - SLACK_CHANNEL_ID=
    restart: unless-stopped
```

## How It Works

1. **Check**: Watchless fetches digests of running container images and compares them with remote registry digests without acutally pulling the new image
2. **Update** (if `AUTO_UPDATE=true`):
   - Pulls the new image
   - Stops the container
   - Removes the old container
   - Recreates the container with the same configuration
   - Starts the new container
   - Reconnects to networks
3. **Cleanup** (if `WATCHLESS_CLEAN=true`):
   - Removes old images that are no longer in use after restarting
4. **Notification**:
   - Sends summary to enabled notification channels 

## Exclusions

### By Container Name
Exclude specific containers by their exact name (comma-separated):
```yaml
- EXCLUDE_CONTAINERS=watchless,nginx-proxy,redis-cache,postgres-main
```

> **Tip**: Always exclude critical infrastructure containers and Watchless itself!

### By Image Pattern
Exclude containers using image name patterns (substring match, comma-separated):
```yaml
- EXCLUDE_IMAGES=postgres,mysql,test-
```

This will exclude any container using images containing "postgres", "mysql", or "test-" in their name.

## Viewing Logs

Check Watchless logs to see what it's doing:
```bash
docker logs watchless

# Follow logs in real-time
docker logs -f watchless

# Show last 100 lines
docker logs --tail 100 watchless
```

## Example Notification

When updates are found and applied, you'll receive a notification like:

```
Docker Update Check Summary
========================================

Updates Available: 2
  • nginx: nginx:latest
  • redis: redis:alpine

Up to Date: 3
  • postgres-main
  • mysql-db
  • app-container

========================================
Update Results
========================================

Successfully Updated: 2
  ✓ nginx: nginx:latest
  ✓ redis: redis:alpine
```

## Advanced Usage

### Run Once Without Scheduling

Don't set `WATCHLESS_SCHEDULE` to run a single check and exit:

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e AUTO_UPDATE=true \
  -e EXCLUDE_CONTAINERS=watchless \
  fish906/watchless:latest
```

### Check Only (No Updates)

Set `AUTO_UPDATE=false` to only check for updates without applying them:

```yaml
environment:
  - AUTO_UPDATE=false
  - WATCHLESS_SCHEDULE=0 0 * * *
  - EMAIL_NOTIFICATION=true
```

### Using Docker Secrets

For sensitive values like passwords, use Docker secrets:

```yaml
version: '3.8'

services:
  watchless:
    image: fish906/watchless:latest
    container_name: watchless
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - AUTO_UPDATE=true
      - EMAIL_NOTIFICATION=true
      - SMTP_SERVER_URL=smtp.mail.com
      - MAIL_SENDER=watchless@example.com
      - MAIL_RECEIVER=admin@example.com
    secrets:
      - smtp_password
    restart: unless-stopped

secrets:
  smtp_password:
    file: ./secrets/smtp_password.txt
```

Then read the secret in your application or pass it as an environment variable.

## Requirements

- Docker Engine with accessible Docker socket
- Running containers to monitor
- Network access to Docker registries for digest comparison

## Security Considerations

- Watchless requires access to the Docker socket (`/var/run/docker.sock`) to manage containers
- Use application-specific passwords for email notifications
- Always exclude critical infrastructure containers from auto-updates, especially when using tags like ':latest'
- Consider using Docker secrets for sensitive values in production

## Building from Source

If you want to build the image yourself:

1. Clone the repository:
```bash
git clone https://github.com/fish906/watchless.git
cd watchless
```

2. Build the image:
```bash
docker build -t watchless:local .
```

3. Run your local build:
```bash
docker run -d \
  --name watchless \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e AUTO_UPDATE=false \
  -e EXCLUDE_CONTAINERS=watchless \
  watchless:local
```

## Support

- [Report Issues](https://github.com/fish906/watchless/issues)
- [Discussions](https://github.com/fish906/watchless/discussions)
- [Documentation](https://github.com/fish906/watchless/wiki)
- [Docker Hub](https://hub.docker.com/r/fish906/watchless)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License
tbd

---

**⚠️ Important**: Always test Watchless in a non-production environment first. While it preserves container configurations, automated updates can still cause service interruptions. Always exclude critical infrastructure containers and the Watchless container itself.