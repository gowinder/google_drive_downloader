# design note

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
  
  
