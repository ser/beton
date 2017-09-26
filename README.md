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

Follow Electrum's documentation: http://docs.electrum.org/en/latest/merchant.html - if not sure, consult #electrum IRC channel @ Freenode.

### Install and prepare Beton

* Create a separate unix user in your system: ```useradd -m beton```
* Install system packages for python and web developement:
 * ```apt install python3-pip python3-wheel python3-setuptools virtualenvwrapper nodejs-legacy npm```
 * ```npm install -g bower```
