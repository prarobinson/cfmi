#!/bin/bash

args=("$@")
PATHS=${args[@]:3}
SUBJECT=$1
FILENAME=$3/$1.$2
EXTEN=$2
TMPDIR=`mktemp -d`

cd $TMPDIR;
mkdir $SUBJECT
cd $SUBJECT
if [ ${EXTEN::3} == "nii" ]; then
    convert.sh $SUBJECT ../ gz=FALSE > convert.log 2>&1
    EXTEN=${EXTEN:4}
else
    index=1
    dscache=""
    for path in $PATHS; do
	firstfile=`ls ${path}/1.ACQ/ | head -1`
	rootname=`strings ${path}/1.ACQ/${firstfile} | grep tProtocolName | awk -F'"' '{print $3}' | sed 's/ /_/g' | sed 's/+/_/g'`
	datestring=`echo ${path} | awk -F"/" '{print $8 $9 $10}'`
	if [ $datestring != $dscache ]; then
	    index=1
	    dscache=$datestring
	fi
	nameNdate="${rootname}_${datestring}"
	ln -s ${path} ${nameNdate}_${index}
	index=$(($index+1))
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
    zip -r $FILENAME.part .
fi
mv $FILENAME.part $FILENAME
rm -rf $TMPDIR
