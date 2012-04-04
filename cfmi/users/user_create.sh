#!/bin/bash

# user_create.sh <uname> <comment> <password>

ssh root@storage001 sh -c "echo $1:$3::mriusers:$2:/home/$1:/bin/bash | newusers; (cd /var/yp; make)"
ssh root@cifs sh -c "smbpasswd -a $1