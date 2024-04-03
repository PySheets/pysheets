clear

export prod=`grep APP_VERSION ../pysheets-prod/app.yaml`
export dev=`grep APP_VERSION app.yaml`
echo "Version in prod:" $prod
echo "Version in dev: " $dev
echo

if [ "$prod" = "$dev" ] ;then 
    echo "Versions in prod and dev are the same."
    echo "Update the version. Cmd+Click here:        app.yaml"
    echo "Then run this script again."
else
    ./build.sh
    if [[ $? -eq 0 ]]; then
        echo "Build succeeded"
        (
            cd ../pysheets-prod;
            git add --all
            git commit -m 'Deploy the latest version'
            git push origin main
            echo "Latest version has been deployed to github. Check DigitalOcean for progress:"
            echo
            echo "https://cloud.digitalocean.com/apps/81140869-ab35-47cc-8afd-d72c51dd9cf4/settings?i=0e0d0e"
            echo
        )
    else
        echo "Build failed"
        exit 1
    fi
    
fi

date