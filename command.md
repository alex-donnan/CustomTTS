*Useful Docker commands for setup*

`docker-compose up -d --build`
- Build the project, creating relevant images and containers

`docker-compose down`
- Kill and remove containers, images remain

`docker exec -it <container_name> /bin/sh`
- Open terminal in container