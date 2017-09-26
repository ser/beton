Beton
=====
 Beton :cocktail: - a Czech drink containing becherovka and tonic

What really is Beton?
---------------------
Beton is a cover plate (frontend) over `Revive Ad Server <https://www.revive-adserver.com/>`_.

It links to Revive via it's XML-RPC API, fully taking over management of ads for your customers. They don't need to see or access original Revive web interface anymore.

Beton adventages over Revive web app:
 - Fully automatic sell system for banners
 - Bitcoin payments via `Electrum <https://electrum.org>`_ wallet merchant service
 
Installation
------------
 
Installation process consists of two main stages, first is installation and configuration of the Revive Ad Server, and second one is installation of Beton itself.

#. Get the newest version of the Revive Ad Server from https://www.revive-adserver.com/download/ - I'm using version 4.1. Install and configure it according to it's documentation. It must be fully working before you move over to next steps.
 #. Create a new advertiser. Note it's Revive's internal ID number.
 #. Add your websites. 
 #. Add zone(s) you want to have within your websites. It must be of *Banner, Button or Rectangle* type.



