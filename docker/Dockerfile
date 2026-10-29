# Training / evaluation image: ROS 2 Foxy (Ubuntu 20.04, Python 3.8) + f110_gym 0.2.1 + PyTorch (CPU).
#   docker build -t f1tenth-rma -f docker/Dockerfile .
#   docker run --rm -it -v $PWD:/f1tenth-rma f1tenth-rma
# Not built in CI (f110_gym pins gym==0.19 / numpy<=1.22). Matches the lab container used in 2026.
FROM ros:foxy

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip git tmux ros-foxy-ackermann-msgs \
    && rm -rf /var/lib/apt/lists/*

# gym==0.19 does not build with modern setuptools/wheel
RUN pip3 install --no-cache-dir "setuptools==65.5.0" "wheel<0.40"

# f1tenth_gym pinned to the commit this repo was checked against
ARG F1TENTH_GYM_REV=4fdb9c7
RUN git clone https://github.com/f1tenth/f1tenth_gym.git /f1tenth_gym \
    && cd /f1tenth_gym && git checkout ${F1TENTH_GYM_REV} \
    && pip3 install --no-cache-dir -e .

RUN pip3 install --no-cache-dir torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu \
    && pip3 install --no-cache-dir "gymnasium==0.29.1" pyyaml "scipy<1.11" tensorboard matplotlib pytest

# TUMFTM raceline optimizer (only for regenerating racelines): broken quadprog wheel fix
#   pip3 install --no-binary quadprog --force-reinstall --no-deps quadprog

WORKDIR /f1tenth-rma
ENV PYTHONPATH=/f1tenth-rma/src/f1tenth_research
CMD ["bash"]
