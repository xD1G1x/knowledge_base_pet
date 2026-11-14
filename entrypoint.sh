
#!/bin/sh

set -e

echo "Waiting for database..."

python manage.py migrate --noinput

echo "Starting Django..."

exec "$@"
