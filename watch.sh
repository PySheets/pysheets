chsum1=""

while [[ true ]]
do
    chsum2=`find static *.py -type f -exec md5 {} \;`
    if [[ $chsum1 != $chsum2 ]] ; then           
        if [ -n "$chsum1" ]; then
            source build.sh > bundle.txt
        fi
        chsum1=$chsum2
    fi
    sleep 1
done