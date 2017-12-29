# Beton
> Beton :cocktail: - a Czech drink containing becherovka and tonic

This software is in active development. You should be an experienced admin of
PHP/Python to start playing with Beton. Strictly no warranty.

## What really is Beton?
Beton is a cover plate (front end) over [Revive Ad Server](https://www.revive-adserver.com/).

It links to Revive via its XML-RPC API, fully taking over management of banner ads for your customers. They don't need to see or access original Revive web interface anymore.

Beton advantages over standard Revive web app:
* Fully automatic sell system for banners
* Independent user base system with auto-registration and email confirmation
* Bitcoin payments via [Electrum](https://electrum.org), your own wallet merchant service (no third parties required!)
* A very clean and responsive interface, based on Bootstrap
 
## Installation
Installation process consists of three main stages. First is installation and configuration of the Revive Ad Server, second is preparation of Electrum payment interface and the third one is installation of Beton itself.

### Install and prepare Revive Ad Server

* Get the newest version of the Revive Ad Server from https://www.revive-adserver.com/download/ - I'm using version 4.1. Install and configure it according to it's documentation. It must be fully working before you move over to next steps.
* Create a new advertiser. Note its Revive's internal ID number.
* Add your websites. 
* Add zone(s) you want to have within your websites. It must be of ```Banner, Button or Rectangle``` type.
* Be sure that SMTP server is working, as Revive will send campaign summaries
directly to customers.

### Install and configure Electrum merchant system

Follow Electrum's documentation: http://docs.electrum.org/en/latest/merchant.html - if not sure, consult #electrum IRC channel @ Freenode. Please install websockets service as well, as it is being used by beton.

After finishing configuration, your ```~/.electrum/config``` should look similar to this, for reference:

```
{
    "requests_dir": "/srv/www/electest", 
    "rpchost": "127.0.0.1", 
    "rpcport": 7707, 
    "ssl_chain": "/etc/pki/realms/random-re/default.crt", 
    "ssl_privkey": "/etc/pki/realms/random-re/default.key", 
    "url_rewrite": [
        "file:///srv/www/", 
        "https://random.re/"
    ], 
    "websocket_port": 9997, 
    "websocket_server": "0.0.0.0"
}
```

### Install and prepare Beton

> This part assumes that you have Ubuntu Xenial 16.04. 

* Create a separate unix user in your system:
  * ```useradd -m beton```
* Install system packages for python and web developement:
  * ```apt install python3-pip python3-wheel python3-setuptools virtualenvwrapper nodejs-legacy npm```
  * ```npm install -g bower```
* Create a virtual python environment for beton and activate it:
  * ```su - beton```
  * ```mkvirtualenv beton```
* When you want to access your environment at a later date, you are just activating it:
  * ```workon beton```
* Clone the beton git repository:
  * ```git clone https://github.com/ser/beton```
* Install required dependencies to your environment
  * ```cd beton```
  * ```pip3 install -r requirements/prod.txt```
  * ```bower install```
  * ```flask db init```
  * ```flask db migrate```
  * ```flask db upgrade```
  
### Configuration of beton

Configuration of beton requires two steps. First is setting up a configuration file, the second one requires setting environment, as you don't want to keep sensitive passwords in the config file itself.

You should create the main configuration file inside the ```beton``` subdirectory with a name ```settings.py```. A template of this file is located in root directory of beton with name ```settings.py.dist```:

```cp settings.py.dist beton/settings.py```

Note that you are able to keep developement and production settings separately. Normally beton uses ```ProdConfig``` class settings, if you set ``` FLASK_DEBUG=1``` in the environment, it will use ```DevConfig``` class instead of. Please remeber it is critically unsafe to run debug mode in production. 

After setting up ```settings.py``` file, you should add environment to the shell running beton. If you use Systemd, this is an example service unit file ```/etc/systemd/system/beton.service```:

```
[Unit]
Description=Beton Ad Server
After=multi-user.target

[Service]
Type=idle
Environment=BETON_SECRET=a_truly_random_characters_about_60_of_them
Environment=REVIVE_MASTER_PASSWORD=password_to_access_main_admin_account_on_revive
Environment=SQLALCHEMY_SQL_PASSWORD=password_to_access_beton_sql_database
Environment=REVIVE_SQL_PASSWORD=password_to_access_revive_sql_database
Environment=MAIL_PASSWORD=password_to_access_smtp_relay_server
Environment=FLASK_APP=/home/beton/beton/autoapp.py
ExecStart=/home/beton/.virtualenvs/beton/bin/flask run --host=127.0.0.1 --port=9234
User=beton

[Install]
WantedBy=multi-user.target
```

When you are ready with all configuration steps, add and enable beton service (as root):

```
# chmod og-wrx /etc/systemd/system/beton.service
# systemctl enable beton.service
# systemctl start beton.service
```

### Configuration of nginx

Instead of serving banners through python or php, it's advised to serve them directly through nginx. It's a suggested nginx configuration snippet:

```
location /beton/ {
         proxy_pass http://127.0.0.1:9234/beton/;
         }
location /beton/banners/ {
         alias /home/beton/beton/beton/banners/;
         }
location /electest/ {
         default_type "application/bitcoin-paymentrequest";
         alias /srv/www/electest/;
         }
```

### Post-install setup

 * Using web interface, add yourself as a user. 
 * Add yourself as an admin manually modifying ```roles``` table. TODO: this step should be automatised in next versions. 
