#!/bin/bash

#######################################################################################################
# What up? This script is designed to convert a subject's dicom (.IMA) images to nii${gzflag}. It takes two
# mandatory arguments: subject id and output directory. It will make subject-specific folders, so the 
# output directory need only be at the study or group level:
#
# >convert.sh Alc45 /exports/cfmi4/home/robinson/Subject_Data/AlcoholStudy/    
#
# The above will try to find and convert ALL of that subject's images, but you can also supply 
# optional parameters - type=[image_type] and/or gz=[TRUE/FALSE] - if you just want to convert a particular
# subset of images or wish to have nii.gz images as output:
#
# >convert.sh Alc45 /exports/cfmi4/home/robinson/Subject_Data/test type=epi
#
########################################################################################################

### Play nice!

renice 19 -p $$

# Let's make sure there are at least the two mandatory args:
if [ $# -lt 2 ]; then
  echo 'Please supply at least the subject id and output directory:'
  echo '  e.g., >convert.sh Alc45 /exports/cfmi4/home/robinson/Subject_Data/Alcohol_Study/   -or-'
  echo '        >convert.sh Alc45 /exports/cfmi4/home/robinson/Subject_Data/Alcohol_Study/ type=t1 '
  echo 'Valid types are: t1, mprage, dti, asl, etc.. it is fairly forgiving :)'
  echo 'This will create a sub-directory in your output directory with the name of the subject id, and append dates and run numbers to each converted image file:' 
  echo '  ~/Subject_Data/Alcohol_Study/Alc45/Siemens_AF8-MPRAGE_PreGelatin_20101001_1.nii' 
  exit
fi

# Here we'll parse the arguments so we can set the imagetype and gz flags if provided:
# Let's default to no .gz
gzflag=""
isgz="N"
tmpdir=`mktemp -d`

for param in $@; do
  argistype=`echo ${param} | grep "type"`
  if [ "${argistype}" != "" ]; then
    imgtype=`echo ${param} | awk -F"=" '{print$2}'`
  else
    gztype=`echo ${param} | awk -F"=" '{print$2}'`
    if [ "${gztype}" == "TRUE" ]; then
      gzflag=".gz"
      isgz="Y"
    fi
  fi
done


echo ${FREESURFER_HOME}
which mri_convert

subjid=${1}
outdir=${2}

# Get the paths and scan names for this subject, if they exist
echo "Getting image info for ${subjid}..."
paths=(`curl -f -k https://imaging.cfmi.georgetown.edu/api/path/${subjid}`)
if [ ${#paths[0]} == 0 ]; then
  echo "No data found for subject ${subjid}...exiting"
else
  if [ ! -e ${outdir}${subjid} ]; then
    mkdir ${outdir}${subjid}
  fi 
  for imgpath in ${paths[*]}; do
    if [ -d ${imgpath}/1.ACQ/ ]; then
      firstfile=`ls ${imgpath}/1.ACQ/ | head -1`
      names=(`strings ${imgpath}/1.ACQ/${firstfile} | grep tProtocolName | awk -F'=' '{print $2}' | sed 's/"//g' | sed 's/ //g' | sed 's/+/_/g'`)
      rootname=${names[${#names[*]}-1]}
    else
      firstfile=`ls ${imgpath}/5.ACQ/ | head -1`
	  names=(`strings ${imgpath}/5.ACQ/${firstfile} | grep tProtocolName | awk -F'=' '{print $2}' | sed 's/"//g' | sed 's/ //g' | sed 's/+/_/g'`)
      rootname=${names[${#names[*]}-1]}
	fi
    imgfiles=(${imgfiles[*]} ${firstfile})
    datestring=`echo ${imgpath} | awk -F"/" '{print $8 $9 $10}'`
    nameNdate="${rootname}_${datestring}"
    imgnames=(${imgnames[*]} ${nameNdate})
  done

  # This just helps keep track of multiple runs having the same name on the same date. 
  ord=1
  
  # Next, let's separate the images by type, making ordinal arrays for each:
  for i in `seq 0 $((${#imgfiles[*]} - 1))`; do
    is_t1=`echo ${imgnames[$i]} | grep MPRAGE`
    if [ "${is_t1}" != "" ]; then 
      T1s=(${T1s[*]} ${i})
      continue
    fi 
    is_dti=`echo ${imgnames[$i]} | grep diff`
    if [ "${is_dti}" != "" ]; then
      DTIs=(${DTIs[*]} ${i}) 
      continue
    fi
    is_asl=`echo ${imgnames[$i]} | grep asl`
    if [ "${is_asl}" != "" ]; then
      ASLs=(${ASLs[*]} ${i}) 
      continue
    fi
    is_epi=`echo ${imgnames[$i]} | grep ep`
    if [ "${is_epi}" != "" ]; then
      otherEPIs=(${otherEPIs[*]} ${i})
      continue
    fi
    is_pdt2=`echo ${imgnames[$i]} | grep PD-T2`
    if [ "${is_pdt2}" != "" ]; then
      PDT2s=(${PDT2s[*]} ${i})
      continue
    fi
    is_pd=`echo ${imgnames[$i]} | grep PD`
    if [ "${is_pd}" != "" ]; then
      PDs=(${PDs[*]} ${i})
    fi
    is_flair=`echo ${imgnames[$i]} | grep FLAIR`
    if [ "${is_flair}" != "" ]; then
      FLAIRs=(${FLAIRs[*]} ${i})
    fi
    is_field=`echo ${imgnames[$i]} | grep field`
    if [ "${is_field}" != "" ]; then
      FIELDs=(${FIELDs[*]} ${i})
    fi
  done

  if [ "${imgtype}" != "" ]; then
    case ${imgtype} in
      "t1"|"T1"|"MPRAGE"|"mprage")
        modality3D=(${T1s[*]})
    ;;
      "PD"|"pd")
        modality3D=(${PDs[*]})
    ;;
      "flair"|"FLAIR")
        modality3D=(${FLAIRs[*]})
    ;;
      "dti"|"DTI"|"diff")
        modality4D=(${DTIs[*]})
    ;;
      "field"|"FIELD"|"fields"|"FIELDS"|"fieldmap"|"FIELDMAP")
        modality3D=(${FIELDs[*]})
    ;;
      "asl"|"ASL"|"casl"|"CASL"|"pasl"|"PASL"|"pcasl"|"PCASL")
        modality4D=(${ASLs[*]})
    ;;
      "epi"|"EPI"|"fmri"|"fMRI"|"rest"|"ep2d")
        modality4D=(${otherEPIs[*]})
    ;;
      "pdt2"|"PDT2"|"pd-t2"|"PD-T2")
        # Both PD and T1 slices are in the same directory, so they must be handled slightly differently:      
        for pdt2 in ${PDT2s[*]}; do
          echo "Converting ${paths[${pdt2}]}/1.ACQ/"
          if [ -e ${outdir}${subjid}/PD_${imgnames[${pdt2}]}_${ord}.nii${gzflag} ]; then
            ord=$((${ord} + 1))
          else
            ord=1
          fi
          files=(`ls ${paths[${pdt2}]}/1.ACQ/`) 
          counter=0
          for file in ${files[*]}; do 
            ln -s ${paths[${pdt2}]}/1.ACQ/${file} ${tmpdir}/${counter}.IMA
            counter=$((${counter} + 1))
          done
          dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/0.IMA
          #mri_convert ${paths[${t1}]}/1.ACQ/${files[0]} ${outdir}${subjid}/${imgnames[${t1}]}_${ord}.nii${gzflag} 
          mv ${tmpdir}/o0.nii${gzflag} ${outdir}${subjid}/PD_${imgnames[${pdt2}]}_${ord}.nii${gzflag}
          mv ${tmpdir}/o1.nii${gzflag} ${outdir}${subjid}/T1_${imgnames[${pdt2}]}_${ord}.nii${gzflag}
          rm ${tmpdir}/* 
        done
    ;;
    esac
    
    for j in ${modality3D[*]}; do
      echo "Converting ${paths[${j}]}/1.ACQ/"
      if [ -e ${outdir}${subjid}/${imgnames[${j}]}_${ord}.nii${gzflag} ]; then
        ord=$((${ord} + 1))
      else
        ord=1
      fi
      files=(`ls ${paths[${j}]}/1.ACQ/`) 
      counter=0
      for file in ${files[*]}; do 
        ln -s ${paths[${j}]}/1.ACQ/${file} ${tmpdir}/${counter}.IMA
        counter=$((${counter} + 1))
      done
      dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/0.IMA
      #mri_convert ${paths[${j}]}/1.ACQ/${files[0]} ${outdir}${subjid}/${imgnames[${j}]}_${ord}.nii${gzflag} 
      niis=(`ls ${tmpdir}/ | grep '^[0-9]*.nii'`)
      orient=`ls ${tmpdir}/ | grep '^o'`
      if [ ${#niis[*]} == 1 ]; then
        mv -v ${tmpdir}/${niis[0]} ${outdir}${subjid}/${imgnames[${j}]}_${ord}.nii${gzflag}
        #mv -v ${tmpdir}/${orient} ${outdir}${subjid}/${imgnames[${j}]}_orient${ord}.nii${gzflag}
      else
        is_field=`echo ${imgnames[$j]} | grep field`
        if [ "${is_field}" != "" ]; then
          type=`strings ${paths[$j]}/1.ACQ/${files[0]} | grep ORIGINAL | awk -F'\' '{print $3}'`
          mv -v ${tmpdir}/0.nii${gzflag} ${outdir}${subjid}/${imgnames[${j}]}_${type}_echo1_${ord}.nii${gzflag}
          mv -v ${tmpdir}/55.nii${gzflag} ${outdir}${subjid}/${imgnames[${j}]}_${type}_echo2_${ord}.nii${gzflag}
        fi
      fi   
      rm ${tmpdir}/* 
    done
      
    for k in ${modality4D[*]}; do
      if [ -d ${paths[${k}]}/1.ACQ/ ]; then
        files=(`ls ${paths[${k}]}/1.ACQ/`)
        is_MOCO=`strings ${paths[${k}]}/1.ACQ/*.IMA | grep -e "MOCO"`
      else
        files=(`ls ${paths[${k}]}/5.ACQ/`)
        is_MOCO=`strings ${paths[${k}]}/5.ACQ/*.IMA | grep -e "MOCO"`
      fi  
      if [ ${#files[*]} == 1 ]; then
        if [ "${is_MOCO}" == "" ]; then
          if [ -e ${outdir}${subjid}/${imgnames[${k}]}_${ord}.nii${gzflag} ]; then
            ord=$((${ord} + 1))
          else
            ord=1
          fi
          for vol in `ls ${paths[${k}]}`; do
            ln -s ${paths[${k}]}/${vol}/* ${tmpdir}/${vol}.IMA
          done
          if [ -e ${tmpdir}/1.ACQ.IMA ]; then
            dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/1.ACQ.IMA
            #mri_convert ${tmpdir}/1.ACQ.IMA ${outdir}${subjid}/${imgnames[${k}]}_${ord}.nii${gzflag}
            mv -v ${tmpdir}/1ACQ.nii${gzflag} ${outdir}${subjid}/${imgnames[${k}]}_${ord}.nii${gzflag}
            if [ -e  ${tmpdir}/1ACQ.bvec ]; then
              mv -v ${tmpdir}/1ACQ.bvec ${outdir}${subjid}/${imgnames[${k}]}_${ord}.bvec
              mv -v ${tmpdir}/1ACQ.bval ${outdir}${subjid}/${imgnames[${k}]}_${ord}.bval
            fi
          else 
            dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/5.ACQ.IMA
            mv -v ${tmpdir}/5ACQ.nii${gzflag} ${outdir}${subjid}/${imgnames[${k}]}_${ord}.nii${gzflag}
          fi
          rm ${tmpdir}/*
        else
          echo "${imgnames[${k}]} is a MOCO series... NOT converting it."
        fi
      else
        echo "Multiple files found in ${paths[${k}]}."
        echo 'For imgtype DTI this is probably just an FA or other computed map; maybe a glm or t-map for fMRI... skipping.'
      fi
    done
  else
 ####### Convert all images if imgtype is not set: ###########################################################
    echo "No image type specified (dti, t1, etc.,): converting all images for subject ${subjid}."
    for l in ${T1s[*]} ${PDs[*]} ${FLAIRs[*]} ${FIELDs[*]}; do
      echo "Converting ${paths[${j}]}/1.ACQ/"
      if [ -e ${outdir}${subjid}/${imgnames[${l}]}_${ord}.nii${gzflag} ]; then
        ord=$((${ord} + 1))
      else
        ord=1
      fi
      if [ -d ${paths[$l]}/1.ACQ/ ]; then
        files=(`ls ${paths[${l}]}/1.ACQ/`) 
        counter=0
        for file in ${files[*]}; do 
          ln -s ${paths[${l}]}/1.ACQ/${file} ${tmpdir}/${counter}.IMA
          counter=$((${counter} + 1))
        done
      else
        files=(`ls ${paths[${l}]}/5.ACQ/`)
        counter=0
        for file in ${files[*]}; do 
          ln -s ${paths[${l}]}/5.ACQ/${file} ${tmpdir}/${counter}.IMA
          counter=$((${counter} + 1))
        done
      fi
      dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/0.IMA
      #mri_convert ${paths[${l}]}/1.ACQ/${files[0]} ${outdir}${subjid}/${imgnames[${l}]}_${ord}.nii${gzflag} 
      niis=(`ls ${tmpdir}/ | grep '^[0-9]*.nii'`)
      orient=`ls ${tmpdir}/ | grep '^o'`
      if [ ${#niis[*]} == 1 ]; then
        mv -v ${tmpdir}/${niis[0]} ${outdir}${subjid}/${imgnames[${l}]}_${ord}.nii${gzflag}
        #mv -v ${tmpdir}/${orient} ${outdir}${subjid}/${imgnames[${l}]}_orient${ord}.nii${gzflag}
      else
        is_field=`echo ${imgnames[$l]} | grep field`
        if [ "${is_field}" != "" ]; then
          type=`strings ${paths[$l]}/1.ACQ/${files[0]} | grep ORIGINAL | awk -F'\' '{print $3}'`
          mv -v ${tmpdir}/0.nii${gzflag} ${outdir}${subjid}/${imgnames[${l}]}_${type}_${ord}_echo1.nii${gzflag}
          mv -v ${tmpdir}/55.nii${gzflag} ${outdir}${subjid}/${imgnames[${l}]}_${type}_${ord}_echo2.nii${gzflag}
        fi
      fi   
      rm ${tmpdir}/* 
    done
    for pdt2 in ${PDT2s[*]}; do
      echo "Converting ${paths[${pdt2}]}/1.ACQ/"
      if [ -e ${outdir}${subjid}/PD_${imgnames[${pdt2}]}_${ord}.nii${gzflag} ]; then
        ord=$((${ord} + 1))
      else
        ord=1
      fi
      files=(`ls ${paths[${pdt2}]}/1.ACQ/`) 
      counter=0
      for file in ${files[*]}; do 
        ln -s ${paths[${pdt2}]}/1.ACQ/${file} ${tmpdir}/${counter}.IMA
        counter=$((${counter} + 1))
      done
      dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/0.IMA
      #mri_convert ${paths[${t1}]}/1.ACQ/${files[0]} ${outdir}${subjid}/${imgnames[${t1}]}_${ord}.nii${gzflag} 
      mv ${tmpdir}/0.nii${gzflag} ${outdir}${subjid}/PD_${imgnames[${pdt2}]}_${ord}.nii${gzflag}
      mv ${tmpdir}/1.nii${gzflag} ${outdir}${subjid}/T1_${imgnames[${pdt2}]}_${ord}.nii${gzflag}
      rm ${tmpdir}/* 
    done
    for m in ${otherEPIs[*]} ${ASLs[*]} ${DTIs[*]}; do
      if [ -d ${paths[${m}]}/1.ACQ/ ]; then
        files=(`ls ${paths[${m}]}/1.ACQ/`)
        is_MOCO=`strings ${paths[${m}]}/1.ACQ/*.IMA | grep -e "MOCO"`
      else
        files=(`ls ${paths[${m}]}/5.ACQ/`)
        is_MOCO=`strings ${paths[${m}]}/5.ACQ/*.IMA | grep -e "MOCO"`
      fi
      if [ ${#files[*]} == 1 ]; then
        if [ "${is_MOCO}" == "" ]; then
          if [ -e ${outdir}${subjid}/${imgnames[${m}]}_${ord}.nii${gzflag} ]; then
            ord=$((${ord} + 1))
          else
            ord=1
          fi
          for vol in `ls ${paths[${m}]}`; do
            ln -s ${paths[${m}]}/${vol}/* ${tmpdir}/${vol}.IMA
          done
          if [ -e ${tmpdir}/1.ACQ.IMA ]; then
            dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/1.ACQ.IMA
            #mri_convert ${tmpdir}/1.ACQ.IMA ${outdir}${subjid}/${imgnames[${m}]}_${ord}.nii${gzflag}
            mv -v ${tmpdir}/1ACQ.nii${gzflag} ${outdir}${subjid}/${imgnames[${m}]}_${ord}.nii${gzflag}
            if [ -e  ${tmpdir}/1ACQ.bvec ]; then
              mv -v ${tmpdir}/1ACQ.bvec ${outdir}${subjid}/${imgnames[${m}]}_${ord}.bvec
              mv -v ${tmpdir}/1ACQ.bval ${outdir}${subjid}/${imgnames[${m}]}_${ord}.bval
            fi
          else 
            dcm2nii -i N -f Y -p N -e N -d N -g ${isgz} ${tmpdir}/5.ACQ.IMA
            mv -v ${tmpdir}/5ACQ.nii${gzflag} ${outdir}${subjid}/${imgnames[${m}]}_${ord}.nii${gzflag}
          fi
          rm ${tmpdir}/*
        else
          echo "${imgnames[${m}]} is a MOCO series... NOT converting it."
        fi
      else
        echo "Multiple files found in ${paths[${m}]}."
        echo 'For imgtype DTI this is probably just an FA or other computed map; maybe a glm or t-map for fMRI... skipping.'
      fi
    done 
  fi
fi 
rm -r ${tmpdir}