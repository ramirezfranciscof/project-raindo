################################################################################
FROM phusion/baseimage:focal-1.0.0

# APT GET BASE INSTALLS
RUN add-apt-repository universe -y && apt-get update && apt-get install -y \
    ###vim-gui-common vim-runtime \
    ###g++ \
    bash-completion \
    python3-venv \
    python3-pip \
    git \
    wget \
    locate \
    libpq-dev \
    graphviz \
    openssh-server \
    vim \
    libkrb5-dev ruby ruby-dev \
    libgdal-dev \
    #apt-transport-https ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install virtualenvwrapper

ENV VIRTUAL_ENV=/root/.virtualenvs/workenv/
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /root
COPY . code
RUN pip install --upgrade pip
RUN pip install -e code
RUN pip install jupyterlab

RUN echo "\nsource .bashrc_extras" >> /root/.bashrc
COPY .docker_config/finalize_init.sh /etc/my_init.d/99_finalize_init.sh
COPY .docker_config/bashrc_extras.sh /root/.bashrc_extras

#CMD ["/sbin/my_init"]
ENV SHELL=/bin/bash
CMD ["jupyter-lab","--ip=0.0.0.0","--no-browser","--allow-root"]
################################################################################
