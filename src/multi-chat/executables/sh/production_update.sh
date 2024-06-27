cd ../..
sudo apt install php-pgsql php-xml php php-curl php-ldap php-redis composer redis php-sqlite3 php-gd php-zip -y
composer install --no-dev --optimize-autoloader --no-interaction
php artisan key:generate --force
php artisan db:seed --class=InitSeeder --force
php artisan migrate --force
rm public/storage
php artisan storage:link
npm install
npm ci --no-audit --no-progress
npm audit fix
php artisan route:cache
php artisan view:cache
php artisan optimize
npm run build
php artisan config:cache