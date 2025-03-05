FROM registry.fedoraproject.org/f33/python3
# Add application sources to a directory that the assemble script expects them
# and set permissions so that the container runs without root access

USER 0
COPY . /tmp/src
RUN /usr/bin/fix-permissions /tmp/src

# Remote debug run
#RUN echo "python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m flask run -h 0.0.0.0 -p 8080" > /opt/app-root/etc/xapp.sh
#RUN chmod 777 /opt/app-root/etc/xapp.sh

USER 1001

# Install the dependencies

RUN python3.9 -m pip install --upgrade pip

RUN /usr/libexec/s2i/assemble

EXPOSE 8080

# Remote debug run: packages
# RUN pip install ptvsd debugpy
# Remote debug run: Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1
# Remote debug run: Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1
# Remote debug run
EXPOSE 5678

# Set the default command for the resulting image
CMD /usr/libexec/s2i/run
