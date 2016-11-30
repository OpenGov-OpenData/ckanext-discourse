## How it works

A new topic is created in the Discourse forum (in a designated Category) for each dataset, organization, and group in the CKAN site.
This will happen automatically the first time someone visits the CKAN dataset, org and group page and starts a discussion. Topic reply counts are also displayed in the appropriate listing pages.

This plugin also supports [ckanext-datarequests](https://github.com/conwetlab/ckanext-datarequests) and [ckanext-showcase](https://github.com/ckan/ckanext-showcase).

## Setup Discourse

1. Install Discourse (v1.6+)

    The recommended way is to use the official Docker image following [these instructions](https://github.com/discourse/discourse/blob/master/docs/INSTALL-cloud.md).

    Heads up! There is an extra step not described in Discourse's install instructions. 

    After the `app.yml` is generated and before bootstrapping, edit the `/containers/app.yml` file and add
    `- git clone https://github.com/TheBunyip/discourse-allow-same-origin.git` to Discourse plugins:

        ```yml

        hooks:
          after_code:
            - exec:
                cd: $home/plugins
                cmd:
                  - mkdir -p plugins
                  - git clone https://github.com/discourse/docker_manager.git
                  - git clone https://github.com/TheBunyip/discourse-allow-same-origin.git
        ```
    Make sure to keep the existing spaces and indentation.

    Also make sure to set up Discourse email integration properly before proceeding as its required for account creation and notification.

2. Create a new Discourse user. This will be the user that will create the topics on Discourse for each CKAN entity that has commenting support (currently, commenting is supported on Dataset packages, Organizations, Groups, Showcase Items, Dataset requests). 

To create a new user, go to "Admin" > "Users" > "Send Invites" and enter an email address. You may want to name the user so that its plainly evident its a bot (e.g. [databot](https://talk.beta.nyc/users/databot/activity)).  After creating the bot user, be sure to verify its email so it can post. (TODO: admin, mod?)

3. Create a new Discourse Category. This will contain all topics created for each CKAN dataset. To do so, go to the homepage and click on "Categories" > "New Category". Enter a name and optionally the slug for your category (e.g. Open Data Talk).  After creating a Category, go to the Category page and take note of the URL.  You will need this to setup ckanext-discourse.

4. Configure Embbedding. Go to "Admin" > "Customize" > "Embedding". You must fill up the following fields:

    * Allowed Hosts: Add the domain (without the http:// bit) of your CKAN instance (e.g. data.myorg.com)
    * Post to Category: Name of the category that you created on step 3 (e.g. Open Data Portal Datasets)
    * Embedding Settings: Username for topic creation: Name of the user that you created on step 2 (e.g. databot)
    * Crawler Settings: 
      * CSS selector for elements that are __allowed in embeds__ - `".module-content"`
      * CSS selector for elements that are __removed from embeds__ - `".ckanext-showcase-launch, .discourse-content, .social, .nums, .follow_button"`
    
5. Configure Oneboxing. Go to "Admin" > "Settings" > "Onebox".  Oneboxing allows users to create a Onebox preview from CKAN URLs.  To create a CKAN onebox in Discourse, just insert a CKAN URL in its own line and one will be created automatically. (Demo [here](https://talk.beta.nyc/t/data-beta-nyc-ckan-customizations))


## Setup CKAN

1. Install ckanext-discourse.

        . /usr/lib/ckan/default/bin/activate
        cd /usr/lib/ckan/default/src
        git clone https://github.com/ontodia/ckanext-discourse
        cd ckanext-discourse
        python setup.py develop

2. Add the `discourse` plugin to the enabled plugins on your ini file:

        ckan.plugins = ... discourse
        
    If discourse embedding is desired for ckanext-showcase and ckanext-datarequests, be sure to add the discourse plugin after those plugins (i.e. ckan.plugins = ... showcase datarequests discourse) 

3. Add the following options as well:

        discourse.url = http://datatalk.myorg.com
        discourse.username = databot
        discourse.ckan_category = c/open-data-talk
        discourse.debug = false

   __discourse.url__: the url of your Discourse instance.  Be sure to specify the full url.  https is supported.
   
   __discourse.username__: the discourse username created earlier.
   
   __discourse.ckan_category__: appended to the discourse.url to get the full URL of the discourse category JSON.  In this example, the webpage for the Discourse CKAN category is http://datatalk.myorg.com/c/open-data-talk.  The plugin automatically adds the ".json" file suffix (i.e. http://datatalk.myorg.com/c/open-data-talk.json) to get the JSON file required to talk to the [Discourse API](https://meta.discourse.org/t/discourse-api-documentation/22706/6).
   
   __discourse.debug__: instead of inserting the JS code to embed a Discourse topic, debugging information is displayed instead. This is useful when troubleshooting, as a misconfigured plugin will "spam" your discourse instance with topics that may annoy your users with false-positive discourse notifications.
