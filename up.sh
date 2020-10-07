# default arg values
BUILD_ENV="development"

# saved as .env file for docker-compose
ENV_FILE=""

# parse kwargs
# for this and other ways check out https://stackoverflow.com/questions/192249/how-do-i-parse-command-line-arguments-in-bash
while [[ $# -gt 0 ]]
do
key="$1"
case $key in
    --build-env|--env)
        if [[ "$2" = prod* ]];
        then
            BUILD_ENV="production"
        fi
        if [[ "$2" = dev* ]];
        then
            BUILD_ENV="development"
        fi
        shift # past argument
        shift # past value
        ;;
    --branch|--overcooked-branch)
        ENV_FILE+="OVERCOOKED_BRANCH=$2
"
        shift # past argument
        shift # past value
        ;;
    --harl-branch)
        ENV_FILE+="HARL_BRANCH=$2
"
        shift # past argument
        shift # past value
        ;;
    --graphics)
        ENV_FILE+="GRAPHICS=$2
"
        shift # past argument
        shift # past value
        ;;
    --agents-dir)
        ENV_FILE+="AGENTS_DIR=$2
"
        shift # past argument
        shift # past value
        ;;
    --trajectories-dir|--trajs-dir)
        ENV_FILE+="TRAJECTORIES_DIR=$2
"
        shift # past argument
        shift # past value
        ;;
    *)    # unknown option
    shift # past argument
;;
esac
done

ENV_FILE+="BUILD_ENV=$BUILD_ENV"
echo "$ENV_FILE" > .env


if [[ "$BUILD_ENV" = "production" ]] ;
then
    echo "production"
    # Completely re-build all images from scatch without using build cache
    docker-compose build --no-cache
    docker-compose up --force-recreate -d
else
    echo "development"
    # Uncomment the following line if there has been an updated to overcooked-ai code
    # docker-compose build --no-cache

    # Force re-build of all images but allow use of build cache if possible
    docker-compose up --build
fi