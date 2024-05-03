clear

export prod=`grep APP_VERSION ../pysheets-prod/app.yaml`
export dev=`grep APP_VERSION app.yaml`
echo "DEPLOY: Version in prod:" $prod
echo "DEPLOY: Version in dev: " $dev
echo

if [ "$prod" = "$dev" ] ;then 
    echo "DEPLOY: Versions in prod and dev are the same."
    echo "DEPLOY: Update the version. Cmd+Click here:        app.yaml"
    echo "DEPLOY: Then run this script again."
else
    ./build.sh norun
    if [[ $? -eq 0 ]]; then
        echo "DEPLOY: Build succeeded"
        (
            cd ../pysheets-prod;
            git add --all
            git commit -m 'Deploy the latest version'
            git push origin main
            echo "DEPLOY: Latest version has been deployed to github. Check DigitalOcean for progress:"
            echo
            echo "DEPLOY: https://cloud.digitalocean.com/apps/81140869-ab35-47cc-8afd-d72c51dd9cf4/settings?i=0e0d0e"
            echo
        )
    else
        echo "DEPLOY: Build failed"
        exit 1
    fi
    
fi

date