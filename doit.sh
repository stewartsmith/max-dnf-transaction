D=${DOCKER:-podman}

d_run ()
{
    $D run -it --rm -v $PWD/dnf-cache:/var/cache/dnf:z -w=$1 -v $PWD/ctx:/mnt:z $2 $3
}

d_build ()
{
    $D build -t $1 -f $2 ctx/
}

container=${container:-fedora}

mkdir -p dnf-cache
mkdir -p ctx/
(echo "FROM $container"; echo "RUN dnf update -y"; echo "RUN dnf makecache") > ctx/Dockerfile.doit
cp max-installable-dnf-transaction.py ctx/
d_build hackery-doit Dockerfile.doit
d_run /mnt hackery-doit "python3 max-installable-dnf-transaction.py $container"
