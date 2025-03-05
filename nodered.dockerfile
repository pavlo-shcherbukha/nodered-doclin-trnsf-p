FROM nodered/node-red

# Define build-time arguments
ARG GIT_USER
ARG GIT_PSW
ARG GIT_BRANCH
ARG GIT_REPO
ARG GIT_EMAIL

RUN rm -rf /data/* /data/.[!.]* /data/..?*

RUN git clone https://${GIT_USER}:${GIT_PSW}@${GIT_REPO} /data -b ${GIT_BRANCH}
RUN git config --global user.email "${GIT_EMAIL}"
RUN git config --global user.name "${GIT_USER}"
RUN cd /data && git pull
RUN cd /data && ls -d */

#RUN cd /data/shcos && npm install
#RUN cd /data/shazblob && npm install
RUN cd /data && npm install


