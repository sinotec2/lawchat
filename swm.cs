# build the image from starting/purging
docker image prune -a
docker build --no-cache -t streamlit .
# build with small modifications
docker build -t streamlit .

# single docker running
docker run -d -e TZ=Asia/Taipei -w /app -v /nas2/sespub/env_laws/json:/app/json -v /nas2/kuang/MyPrograms/streamlit/lawchat/access.log:/app/access.log -v /home/kuang/.streamlit/secrets.toml:/root/.streamlit/secrets.toml -p 8501:8501 --name env_law streamlit:latest

docker run -d -e TZ=Asia/Taipei -w /app \
-v /nas2/sespub/env_laws/json:/app/json \
-v /nas2/kuang/MyPrograms/streamlit/lawchat/ip_email.csv:/app/ip_email.csv \
-v /nas2/kuang/MyPrograms/streamlit/lawchat/data:/app/data \
-v /home/kuang/.streamlit/secrets.toml:/root/.streamlit/secrets.toml \
-p 8501:8501 --name env_law streamlit:latest

#sleep mode for testing
docker run -d --entrypoint "/bin/sh" streamlit:latest -c "sleep infinity"

# swarm dockers
#initiate once
docker swarm init --advertise-addr 172.20.31.1

# by joinning (first time)
docker swarm join --token SWMTKN-1-1mrjlqrjuknz1t4ok10z2x1k8byfhw2ujub52uqaqk1ursm0tz-7xlifnnytqg9cve0pfs9e18c4 172.20.31.1:2377

# network creating if additional docker is added to same network
docker network rm lawstack_default  
docker network create --driver overlay --attachable lawstack_default  
docker network inspect lawstack_default  

# by stackking
docker stack deploy -c docker-compose.yml lawstack

#check
docker service ls
docker service ps lawstack_env_law
docker service ps lawstack_env_law --format '{{.ID}}: {{.Name}} - {{.Ports}}'
docker service inspect lawstack_env_law --format '{{json .Endpoint.Ports}}'
docker stack ps lawstack  


# stop the swarm
docker service rm lawstack_env_law
docker swarm leave --force  

#neo4j docker

docker run \
    -p 7474:7474 -p 7687:7687 \
    -v $PWD/neo4j_node01:/data -v $PWD/plugins:/plugins \
    --name neo4j-apoc \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    -e NEO4JLABS_PLUGINS=\[\"apoc\"\] \
    -d \
    neo4j:latest

# qdrant server
# standalone
docker run -d -p 6333:6333 -v $(pwd)/data/raptor_dbs:/qdrant/storage --name raptor_qdrant qdrant/qdrant  
# on swarm network
docker-compose -f docker-composeQ.yaml up -d
