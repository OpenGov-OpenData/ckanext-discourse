## How it works

A new topic is created in the Discourse forum (in a designated Category) for each dataset, organization, and group in the CKAN site.
This will happen automatically the first time someone visits the CKAN dataset, org and group page and starts a discussion. Topic reply counts are also displayed in the appropriate listing pages.

This plugin also supports [ckanext-datarequests](https://github.com/conwetlab/ckanext-datarequests) and [ckanext-showcase](https://github.com/ckan/ckanext-showcase).

## Setup Discourse

1. Install Discourse.

    The recommended way is to use the official Docker image following [these instructions](https://github.com/discourse/discourse/blob/master/docs/INSTALL-cloud.md), but read below first.

    You will need to install [Docker](https://www.docker.com/) first.

    Heads up! There is an extra step, not described in these instructions, before bootstraping your application to allow the Discourse comments to be embbeded on different domains.
    Edit the `containers/app.yml` file and add the last line (`- git clone https://github.com/TheBunyip/discourse-allow-same-origin.git`) to this snippet:

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

    Also make sure to set up emailing properly and to create an admin account as described in the instructions.

2. Create a new Discourse user. This will be the user that will create the topics on Discourse for each CKAN dataset. To create a new user, go to "Admin" > "Users" > "Send Invites" and enter an email address. You may want to name the user so that its plainly evident its a bot (e.g. [databot](https://talk.beta.nyc/users/databot/activity)) (TODO: admin, mod?)

3. Create a new Discourse Category. This will contain all topics created for each CKAN dataset. To do so, go to the homepage and click on "Categories" > "New Category". Enter a name and optionally the slug for your category.  After creating a Category, go to the Category page and take note of the URL.  You will need this to setup ckanext-discourse.

4. Configure Embbedding. Go to "Admin" > "Settings" > "Embedding". You must fill up the following fields:

    * embeddable hosts: Add the domain (without the http:// bit) of your CKAN instance (e.g. data.myorg.com)
    * embed by username: Name of the user that you created on step 2 (e.g. portaldatabot)
    * embed category: Name of the category that you created on step 3 (e.g. Open Data Portal Datasets)
    
5. Configure Oneboxing. Go to "Admin" > "Settings" > "Onebox".  Be sure the CKAN domain is in the whitelist. Oneboxing allows users to create a Onebox preview from CKAN URLs.  To create a CKAN onebox in Discourse, just insert a CKAN URL in its own line and one will be created automatically. (Demo [here](https://talk.beta.nyc/t/data-beta-nyc-ckan-customizations))


## Setup CKAN

1. Install ckanext-discourse. Activate your virtualenv and run:

        git clone https://github.com/okfn/ckanext-discourse.git
        cd ckanext-discourse
        python setup.py develop

2. Add the `discourse` plugin to the enabled plugins on your ini file:

        ckan.plugins = ... discourse
        
    If discourse embedding is desired for ckanext-showcase and ckanext-datarequests, be sure to add the discourse plugin after those plugins (i.e. ckan.plugins = ... showcase datarequests discourse) 

3. Add the following options as well:

        discourse.url=http://discourse.example.com
        discourse.username=ddhdatabot
        discourse.ckan_category=c/data-discovery-hub-datasets
        discourse.debug = false

   __discourse.url__: the url of your Discourse instance.  Be sure to specify the full url.  https is supported.
   
   __discourse.username__: the discourse username created earlier.
   
   __discourse.ckan_category__: appended to the discourse.url to get the full URL of the discourse category JSON.  In this example, the webpage for the Discourse CKAN category is http://discourse.example.com/c/data-discovery-hub-datasets.  The plugin automatically adds the ".json" file suffix (i.e. http://discourse.example.com/c/data-discovery-hub-datasets.json) to get the JSON file required to talk to the [Discourse API](https://meta.discourse.org/t/discourse-api-documentation/22706/6).
   
   __discourse.debug__: instead of inserting the JS code to embed a Discourse topic, debugging information is displayed instead. This is useful when troubleshooting, as a misconfigured plugin will "spam" your discourse instance with topics that may annoy your users with false-positive discourse notifications.
