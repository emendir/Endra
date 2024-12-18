FROM local/walytis_auth_testing:latest
WORKDIR /opt/Endra
COPY . /opt/Endra

RUN pip install --break-system-packages --root-user-action ignore -r /opt/Endra/requirements-dev.txt
RUN pip install --break-system-packages --root-user-action ignore -r /opt/Endra/requirements.txt
RUN for SUBFOLDER in /opt/Endra/tests/endra_docker/python_packages/*; do pip install --break-system-packages --root-user-action ignore "$SUBFOLDER"; done


RUN pip install --break-system-packages --root-user-action ignore -e /opt/Endra

# REMOVE THIS when a stable version of WalIdentity is put into requirements.txt
RUN pip install --break-system-packages --root-user-action ignore -e /opt/WalIdentity


# RUN pip show WalIdentity
## Run with:
# docker run -it --privileged local/endra_testing