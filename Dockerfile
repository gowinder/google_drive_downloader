FROM gowinder/pipenv-alpine
RUN apk update && apk add python3 pipenv