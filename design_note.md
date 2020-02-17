# design note

## database

### worker

| column  | type  | desc |
|---|---|---|
| id  | str  |  drive id |
| title | str | drive title |
| status | int | worker status |
| error | str | last error |
| last_update | str | last_update_time |


### drive_list

store all the file list of drive

| column  | type  | desc |
|---|---|---|
| id  | str  |  drive id |
| title | str | drive title |
| worker_id | int | worker drive id |
| parent_id | int | parent drive id |
| mine_type | str | file mime type |
| size | int | file size |
| status | int | file download status |
| error | str | file download error |
| copy_id | str | copied file id, if exists |
| download_flag | int | if need download |



## background coroutine

### coroutine

#### maintainer
  maintain the download job list, sync download status and database
  
#### download worker

  download job

#### status

* init: start up
* listing: retrive google drive id file list
* download

##### download status

a sub status when worker status is download

* downloading
* make copy
* error
* done
  
### coroutine communication queue

* main queue
  1. produce by download worker, inform work download status, consume by maintainer coroutine
  2. produce by web front request handler, inform action like cancel, delete start job, consume by maintianer coroutine.
* worker queue
  every work has its own queue, inform by maintianer coroutine, receive job action
  
  
