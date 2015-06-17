## How it works

TODO: expand

A new topic is created in the Discourse forum (in a designated Category) for each dataset in the CKAN site.
This will happen automatically the first time someone visits the CKAN dataset page


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

2. Create a new Discourse user. This will be the user that will create the topics on Discourse for each CKAN dataset. To create a new user, go to "Admin" > "Users" > "Send Invites" and enter an email address. (TODO: admin, mod?)

3. Create a new Discourse Category. This will contain all topics created for each CKAN dataset. To do so, go to the homepage and click on "Categories" > "New Category". Enter a name and optionally the slug (URL) for your category.

4. Configure Embbedding. Go to "Admin" > "Settings" > "Embedding". You must fill up the following fields:

    * embeddable hosts: Add the domain (without the http:// bit) of your CKAN instance (eg data.myorg.com)
    * embed by username: Name of the user that you created on step 2 (eg portaldatasets)
    * embed category: Name of the category that you created on step 3 (eg Open Data Portal Datasets)


## Setup CKAN

1. Install ckanext-discourse. Activate your virtualenv and run:

        git clone https://github.com/okfn/ckanext-discourse.git
        cd ckanext-discourse
        python setup.py develop

2. Add the `discourse` plugin to the enabled plugins on your ini file:

        ckan.plugins = ... discourse

3. Add the following options as well:
    TODO: expand

        discourse.url=http://discourse.example.com
        discourse.username=ddhdatasets
        discourse.ckan_category=c/data-discovery-hub-datasets.json
