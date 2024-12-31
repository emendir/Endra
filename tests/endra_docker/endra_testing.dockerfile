FROM local/endra_prereqs:latest
WORKDIR /opt/Endra
COPY . /opt/Endra

# update the already-installed editable WalIdentity python package
RUN /bin/rsync -XAva tests/endra_docker/python_packages/WalIdentity /opt/
