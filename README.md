# Beton ![Python3](https://www.shareicon.net/data/128x128/2016/07/16/634601_python_512x512.png)
> Beton :cocktail: - a Czech drink containing becherovka and tonic

This software is in active developement. You should be an experienced admin of
PHP/Python to start playing with Beton. Strictly no warranty.

## What really is Beton?
Beton is a cover plate (frontend) over [Revive Ad Server](https://www.revive-adserver.com/).

It links to Revive via it's XML-RPC API, fully taking over management of ads for your customers. They don't need to see or access original Revive web interface anymore.

Beton adventages over standar Revive web app:
* Fully automatic sell system for banners
* Bitcoin payments via [Electrum](https://electrum.org) your own wallet merchant service (no third parties required!)
* A very clean and responsive interface, based on Bootstrap
 
## Installation
Installation process consists of three main stages, first is installation and configuration of the Revive Ad Server, second is preparation of Electrum payment interface and the third one is installation of Beton itself.

### Install and prepare Revive Ad Server

* Get the newest version of the Revive Ad Server from https://www.revive-adserver.com/download/ - I'm using version 4.1. Install and configure it according to it's documentation. It must be fully working before you move over to next steps.
* Create a new advertiser. Note its Revive's internal ID number.
* Add your websites. 
* Add zone(s) you want to have within your websites. It must be of ```Banner, Button or Rectangle``` type.

### Install and configure Electrum merchant system

Follow Electrum's documentation: http://docs.electrum.org/en/latest/merchant.html

### Install and prepare Beton

* Create a separate user in your system: ```useradd -m beton```

