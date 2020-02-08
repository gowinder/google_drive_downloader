# download google drive shared folder

## first need a google drive api

go to `https://console.developers.google.com/apis/credentials/oauthclient`

get a client id and secret, select `other application`, not `web application`

and download `client_secret_xxx-yyy.apps.googleusercontent.com`, `xxx-yyy` is different from here

rename it to `client_secrets.json` and place it in root folder

## install depend package

`pip install -r requirements.txt`

## run cmd

`python3 main.py --driveid shared_id --downdir ~/download_folder`

at first will show auth link, open it with browser and get the secrets from google auth page

then it will download all file include sub folder in shared folder

## note

* when break down, it will check downloaded files
* it will skip download file when file size it the same
* it will continue download when local size is less than remote
* it will over write local file when local size is more than remote


## TODO

* rename root folder from remote title
* add Dockerfile
* show download speed
* download queue
* multi-thread download
* support proxy
