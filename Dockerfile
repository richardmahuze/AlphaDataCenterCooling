FROM ubuntu:22.04

# Install required packages
RUN 	apt-get update && \
    	apt-get install -y \
    	wget \
    	curl \
    	libgfortran5 \
    	&& rm -rf /var/lib/apt/lists/*

# Set the user to root to have permissions to install packages
USER root

# Install commands for Spawn
ENV SPAWN_VERSION=0.3.0-8d93151657
RUN wget https://spawn.s3.amazonaws.com/custom/Spawn-$SPAWN_VERSION-Linux.tar.gz \
    && tar -xzf Spawn-$SPAWN_VERSION-Linux.tar.gz \
    && ln -s /Spawn-$SPAWN_VERSION-Linux/bin/spawn-$SPAWN_VERSION /usr/local/bin/

# Create new user
RUN 	useradd -ms /bin/bash user
USER user
ENV 	HOME /home/user

# Download and install miniconda and create environment from yml
COPY AlphaDataCenterCooling_Gym/environment.yml $HOME/environment.yml
RUN 	cd $HOME && \
	wget https://repo.anaconda.com/miniconda/Miniconda3-py310_23.1.0-1-Linux-x86_64.sh -O $HOME/miniconda.sh && \
	/bin/bash $HOME/miniconda.sh -b -p $HOME/miniconda && \
	$HOME/miniconda/bin/conda config --set always_yes yes --set changeps1 no && \
	$HOME/miniconda/bin/conda config --add channels conda-forge && \
	$HOME/miniconda/bin/conda config --set channel_priority strict && \
	$HOME/miniconda/bin/conda update -n base -c conda-forge conda && \
	$HOME/miniconda/bin/conda env create -f environment.yml

WORKDIR $HOME


ENV PYTHONPATH $PYTHONPATH:$HOME

CMD ["/bin/bash", "-c", "source $HOME/miniconda/bin/activate && conda activate AlphaDataCenterCooling && python restapi.py"]

EXPOSE 5000
