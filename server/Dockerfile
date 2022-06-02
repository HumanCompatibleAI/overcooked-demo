FROM python:3.8 as tf

##This part of code installs bazel which we can further use to rebuilt libraries packages for m1 support
#RUN apt-get update
#RUN DEBIAN_FRONTEND=noninteractive apt-get -y install build-essential openjdk-11-jdk zip unzip wget
#RUN wget https://github.com/bazelbuild/bazel/releases/download/4.2.1/bazel-4.2.1-dist.zip
#RUN mkdir bazel-4.2.1mkdir bazel-4.2.1
#RUN unzip -d ./bazel-4.2.1 bazel-4.2.1-dist.zip
#WORKDIR /bazel-4.2.1
#RUN env EXTRA_BAZEL_ARGS="--host_javabase=@local_jdk//:jdk" bash ./compile.sh
#RUN cp output/bazel /usr/local/bin
#WORKDIR /
#RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -y
#RUN cargo install py-spy \

ARG M1
ARG BUILD_ENV
ARG OVERCOOKED_BRANCH
ARG HARL_BRANCH
ARG GRAPHICS
#
WORKDIR /app
#
# Install non-chai dependencies

RUN pip install --upgrade pip
RUN apt-get update && apt-get -y install cmake

if [ "$M1" = "false" ]; then COPY ./requirements.txt ./requirements.txt; else COPY ./requirements_m1.txt ./requirements.txt ; fi \

#Here comes the problem, it's a built version 1.1.0 which will work, but then we will need
#to change some parts of the code, other way is to rebuild the version 0.8.5
if [ "$M1" = "true" ]; then RUN wget https://github.com/ray-project/ray/files/5741700/ray-1.1.0-cp38-aarch64.zip ; fi
if [ "$M1" = "true" ]; then RUN unzip ray-1.1.0-cp38-aarch64.zip ; fi
if [ "$M1" = "true" ]; then RUN pip install ray-1.1.0-cp38-cp38-linux_aarch64.whl ; fi
if [ "$M1" = "true" ]; then RUN pip install py_spy-0.3.3-cp38-cp38-linux_aarch64.whl ; fi
if [ "$M1" = "true" ]; then RUN pip install tensorflow==2.6.0 -f https://tf.kmtea.eu/whl/stable.html ; fi
if [ "$M1" = "true" ]; then RUN pip install -r requirements.txt ; fi
##
## Install eventlet production server if production build
RUN if [ "$BUILD_ENV" = "production" ] ; then pip install eventlet ; fi
##
## Clone chai code
RUN git clone https://github.com/HumanCompatibleAI/overcooked_ai.git --branch $OVERCOOKED_BRANCH --single-branch /overcooked_ai
RUN git clone https://github.com/HumanCompatibleAI/human_aware_rl.git --branch $HARL_BRANCH --single-branch /human_aware_rl
##
if [ "$M1" = "true" ]; then COPY ./setup_corrections/setup.py /human_aware_rl/setup.py ; fi

#I've started to upgrade ray to 1.1.0 version (it requires to use different (upgraded) class for RNN)
##COPY ./setup_corrections/ppo_rlib.py /human_aware_rl/human_aware_rl/ppo/ppo_rllib.py

## Dummy data_dir so things don't break
RUN echo "import os; DATA_DIR=os.path.abspath('.')" >> /human_aware_rl/human_aware_rl/data_dir.py
##

### Install chai dependencies
RUN pip install -e /overcooked_ai
RUN pip install -e /human_aware_rl

##
RUN apt-get install -y libgl1-mesa-dev
##

### Copy over remaining files
COPY ./static ./static
COPY ./*.py ./
COPY ./graphics/$GRAPHICS ./static/js/graphics.js
COPY ./config.json ./config.json
##
## Set environment variables that will be used by app.py
ENV HOST 0.0.0.0
ENV PORT 5000
ENV CONF_PATH config.json
##
## Do the thing
EXPOSE 5000
CMD ["python", "-u", "app.py"]