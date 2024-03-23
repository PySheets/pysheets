clear

printf  "Did you update the version in app.yaml? (y/n) " yn
read answer

if [ "$answer" = "y" ] ;then 
    source build.sh
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
fi