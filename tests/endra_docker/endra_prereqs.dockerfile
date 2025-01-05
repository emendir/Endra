FROM local/walytis_auth_testing:latest
WORKDIR /opt/Endra
COPY . /opt/Endra

# update the already-installed editable WalIdentity python package
RUN /bin/rsync -XAva tests/endra_docker/python_packages/WalIdentity /opt/

RUN pip install --break-system-packages --root-user-action ignore -r /opt/Endra/requirements-dev.txt
RUN pip install --break-system-packages --root-user-action ignore -r /opt/Endra/requirements.txt
RUN for SUBFOLDER in /opt/Endra/tests/endra_docker/python_packages/*; do pip install --break-system-packages --root-user-action ignore -e "$SUBFOLDER"; done


RUN pip install --break-system-packages --root-user-action ignore -e /opt/Endra


# RUN pip show WalIdentity
## Run with:
# docker run -it --privileged local/endra_testing