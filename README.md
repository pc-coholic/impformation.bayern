impformation.bayern - aka: BayIMCO Appointment Checker Toolkit - Server Edition™
================================================================================

This is a quick and dirty bot, that checks every time it is called if there are any new available vaccination 
appointments available within the BayIMCO system. It is loosely based on https://github.com/pc-coholic/c19ac, which 
only checked for one specific user.

While c19ac only checked for one user and this checks all available vaccination centers in Bavaria, there is probably 
no need for you to run this yourself: The generated information is available at https://impformation.bayern/. Let's 
be nice to the BayIMCO-servers and have only a single instance poll the data, okay?

**Available Data Sources**

* https://impformation.bayern/vaccines.json:
  
    A list of all vaccines known to BayIMCO. The ID will be returned in the `appointments.json`

* https://impformation.bayern/districts.json:

    A list of Districts (*Bezirke*) with their principal (`type: MAIN`) vaccination centers, addresses, secondary 
    vaccination centers and more. Getting the `siteIds` from here will allow you to create a list of all vaccination
    sites (A single vaccination center might have multiple sites - think: Main Vaccination Center, Mobile Vaccination 
    Bus). This list only includes the address of the main site - but by querying with the `id` of the center, we can 
    get a complete list of all vaccination sites includes their addresses.
  
* https://impformation.bayern/centers.json:
    
    For your convenience: A list of all vaccination center `id` per district.
  
* https://impformation.bayern/sites.json:

    A list of all vaccination center sites, keyed by their `siteId` (UUID) and including their center's `Id` (remember: 
    one center can have multiple sites!), `name`, `type` (`MAIN` || `SECONDARY`) and the site's `address`. If the site 
    has no address on file (mostly debugging-/development-sites), the `address`-attribute will be `null`. Else it will 
    contain a dict with the address.
  
* https://impformation.bayern/appointments.json:

    The same file as `sites.json`, but each site has a few more attributes:
    * `first_available`:
      * `null` if no upcoming available vaccination appoint could be determined
      * dict of `date`, `time`, `vaccine` if an upcoming available vaccination appoint could be determined
    * `lastcheck`: DateTime when we last touched/checked this site.
  
* https://impformation.bayern/appointments60.json:

    The same file as `appointments.json`, but this time we list the available appointments for people over the age of 
    60. Since (as of 07.04.2021) AstraZeneca is only recommended for to people over the age of 60, expect to see a lot 
    more appointments available with this vaccine in this file and probably not a single one in the `appointments.json`.
    

If you want to build your own service, polling `appointments.json` and `appointments60.json` on a regular base should 
probably be more than enough. At this point, we are aiming to provide an update approximately every 5 minutes.

In the near future, the separate `appointment.json`-files will be merged into a single one with a better syntax. 


**Abuse Contact**

https://impformation.bayern/ will set an `X-Abuse-Contact` on every request sent. BayIMCO staff may contact me through 
the information contained therein. You can also request my contact information through the coordination staff of 
Center 119.
