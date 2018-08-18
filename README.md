# Setup
All commands should be executed from the root of the repository unless stated
otherwise  
A preceding `#` indicates a command should be run as root

## nginx
See [aiohttp docs](https://docs.aiohttp.org/en/stable/deployment.html#nginx-configuration)
1. Link the repository directory to the standard web files location  
`# ln -s "$(readlink -f .)" /srv/http/fossfund`
2. Use the provided [nginx.conf](nginx.conf) as the nginx configuration file  
`# ln -s "$(readlink -f nginx.conf)" /etc/nginx/nginx.conf`

## PostgreSQL
1. Setup the data directory  
`# sudo -Hu postgres sh -c "initdb -D /var/lib/postgres/data"`
2. Start PostgreSQL  
`# systemctl start postgresql`
3. Create the user and database  
`# sudo -Hu postgres sh -c "createuser fossfund; createdb fossfund"`
4. Enable the `uuid-ossp` extension  
`# sudo -Hu postgres sh -c "psql -d fossfund -c 'CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";'" `

## Application
1. Install the PyPI dependencies  
`$ pip install -r require.pip`
2. Setup the database schema  
`$ python -m fossfund.__init__ setup`

# Running
1. Start PostgreSQL and nginx  
`# systemctl start nginx postgresql`
2. Start Gunicorn  
`$ gunicorn -c gunicorn.py fossfund:app`
