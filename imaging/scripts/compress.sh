#!/bin/bash

args=("$@")
SUBJECT=$1
FILENAME=$3/$1.$2
EXTEN=$2
EMAIL=$4
TMPDIR=`mktemp -d`
PATHS=`curl -f -k https://imaging.cfmi.georgetown.edu/api/path/${SUBJECT}`
TEMPLATE=$HOME/cfmi/imaging/templates/email.tpl

echo "$@" >> /tmp/wtf.log

cd $TMPDIR;
mkdir $SUBJECT
cd $SUBJECT
if [ ${EXTEN::3} == "nii" ]; then
    convert.sh $SUBJECT ./ gz=FALSE > convert.log 2>&1
    mv convert.log $SUBJECT
    EXTEN=${EXTEN:4}
else
    index=1
    dscache=""
    for path in $PATHS; do
	if [ -d ${path}/1.ACQ/ ]; then
	    firstfile=`ls ${path}/1.ACQ/ | head -1`
	    rootname=`strings ${path}/1.ACQ/${firstfile} | grep tProtocolName | awk -F'=' '{print $2}' | sed 's/"//g' | sed 's/ //g' | sed 's/+/_/g'`
	else
	    firstfile=`ls ${path}/5.ACQ/ | head -1`
	    rootname=`strings ${path}/5.ACQ/${firstfile} | grep tProtocolName |  awk -F'=' '{print $2}' | sed 's/"//g' | sed 's/ //g' | sed 's/+/_/g'`
	fi
	if [ -z "$rootname" ]; then
	    continue
	fi
	datestring=`echo ${path} | awk -F"/" '{print $8 $9 $10}'`
	if [ "$datestring" != "$dscache" ]; then
	    index=1
	    dscache=$datestring
	fi
	nameNdate="${rootname}_${datestring}"
	if [ -n "$rootname" ]; then
	    ln -s ${path} "${nameNdate}_${index}"
	    index=$(($index+1))
	fi
    done
    cd $TMPDIR
fi

if [ $EXTEN == "tar" ]; then
    tar -chf $FILENAME.part .
fi
if [ $EXTEN == "tar.gz" ]; then
    tar -czhf $FILENAME.part .
fi
if [ $EXTEN == "tar.bz2" ]; then
    tar -cjhf $FILENAME.part .
fi
if [ $EXTEN == "tar.xz" ]; then
    tar -cJhf $FILENAME.part .
fi
if [ $EXTEN == "zip" ]; then
    rm $FILENAME.part
    zip -r $FILENAME.part .
fi
# Don't clobber in the rare case another worker has already finished
mv -n $FILENAME.part $FILENAME
rm -rf $TMPDIR

sed -e "s/{{ subject }}/$SUBJECT/" $TEMPLATE | \
    sed -e "s,{{ url }},https://imaging.cfmi.georgetown.edu/download/${SUBJECT}.${EXTEN}," | \
    mail -s "File is ready" -r imaging@cfmi.georgetown.edu $EMAIL
