FROM lambci/lambda:build-python3.6
COPY .aws /root/.aws
WORKDIR /usr/src/app