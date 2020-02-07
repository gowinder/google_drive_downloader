# download google drive shared folder

## first need a google drive api

go to `https://console.developers.google.com/apis/credentials/oauthclient`

get a client id and secret, select `other application`, not `web application`

and download `client_secret_xxx-yyy.apps.googleusercontent.com`, `xxx-yyy` is different from here

rename it to `client_secrets.json` and place it in root folder

## install depend package

`pipenv install`

## run cmd

`python3 main.py --driveid shared_id --downdir ~/download_folder`

it will download all file include sub folder in shared folder

## note

* when break down, it will check downloaded files
* it will skip download file when file size it the same
* it will continue download when local size is less than remote
* it will over write local file when local size is more than remote


## TODO

* rename root folder from remote title
* add Dockerfile
