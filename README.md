# Beton
> Beton :cocktail: - a Czech drink containing becherovka and tonic

This software is in active development. You should be an experienced admin of
PHP/Python to start playing with Beton. Strictly no warranty. 

[Sponsor this project](https://liberapay.com/ser/donate)

## What really is Beton?
Beton was before cover plate (front end) over [Revive Ad Server](https://www.revive-adserver.com/). You still can find this work in `revive` branch. Now it is an independent adserver tightly connected to nginx as it uses nginx logging to get stats.

Beton advantages over known oopen source banner systems:
* Fully automatic sell system for banners
* Independent user base system with auto-registration and email confirmation
* Bitcoin payments via [btcpayserver](https://btcpayserver.org), your own fully open-source cryptocurrency payment processor (no third parties required!)
* A very clean and responsive interface, based on Bootstrap
* Adblock masking
 
## Installation
Installation process consists of three main stages. First is installation and configuration of the beton Ad Server, second is installation and configuration of btcpayserver, and the third one is installation of nginx rules.

### Install and configure BTCpayserver

Follow btcpayserver's documentation: https://btcpayserver.org/

### Install and prepare Beton

> This part assumes that you have Ubuntu Xenial 16.04. 

* Create a separate unix user in your system:
  * ```useradd -m beton```
* Install system packages for python and web developement:
  * ```apt install python3-pip python3-wheel python3-setuptools python3-dev nodejs-legacy npm```
  * ```npm install -g bower```
* Clone the beton git repository:
  * ```git clone https://github.com/ser/beton```
* Install required dependencies to your environment
  * ```cd beton```
  * ```pip3 install -r requirements/prod.txt```
  * ```bower install```
  
### Configuration of beton

Configuration of beton requires two steps. First is setting up a configuration file, the second one requires setting environment, as you don't want to keep sensitive passwords in the config file itself.

You should create the main configuration file inside the ```beton``` subdirectory with a name ```settings.py```. A template of this file is located in root directory of beton with name ```settings.py.dist```:

```cp settings.py.dist beton/settings.py```

Note that you are able to keep developement and production settings separately. Normally beton uses ```ProdConfig``` class settings, if you set ``` FLASK_DEBUG=1``` in the environment, it will use ```DevConfig``` class instead of. Please remeber it is critically unsafe to run debug mode in production. 

After setting up ```settings.py``` file, you should add environment to the shell running beton. If you use UWSGI (you should!), an example ```beton.ini``` is included in this repository main directory.

When you are ready with settings and setting environment in systemd, you should export the environment locally once to inititate the database, being logged as the user which runs Beton:

```
beton$ export BETON_SECRET=a_truly_random_characters_about_60_of_them
beton$ export SQLALCHEMY_SQL_PASSWORD=password_to_access_beton_sql_database¬
beton$ export MAIL_PASSWORD=password_to_access_smtp_relay_server
beton$ export FLASK_APP=/home/beton/beton/autoapp.py
beton$ export FLASK_DEBUG=1
beton$ export FLASK_ENV=development

beton$ flask db init
beton$ flask db migrate
beton$ flask db upgrade
```

When you are ready with all configuration steps, add and enable UWSGI service (as root).

### Configuration of nginx

Instead of serving banners through python or php, it's advised to serve them directly through nginx. It's a suggested nginx configuration snippet:

```
location /beton/ {
         uwsgi_pass 127.0.0.1:9234;
         }
location /beton/banners/ {
         alias /home/beton/beton/beton/banners/;
         }
```

### Post-install setup

 * Using web interface, add yourself as a user. 
 * Add yourself as an admin manually modifying ```roles``` table. TODO: this step should be automatised in next versions:
 ```
 mysql> select * from roles;
+----+-------+---------+
| id | name  | user_id |
+----+-------+---------+
|  1 | admin |       2 |
+----+-------+---------+
1 row in set (0.00 sec)
 ```
### Screen shots

<img src="https://random.re/_media/faq/screen_shot_2019-03-13_at_20.36.14-fullpage.png" width=800>
