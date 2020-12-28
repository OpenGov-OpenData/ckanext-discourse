import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import requests
import time
import sys
import re
import pylons
import json
import ckan.plugins as p
from ckan.plugins.toolkit import asbool
from ckan.common import g, config
from ckanext.discourse.interfaces import IDiscourse

from discourse_api import DiscourseApi

import ckan.lib.jobs as jobs

import logging

log = logging.getLogger(__name__)

get_action = logic.get_action

class DiscoursePlugin(plugins.SingletonPlugin):
    """
    Insert javascript fragments into package pages and the home page to
    allow users to view and create comments on any package.
    """
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IPackageController, inherit=True)

    def configure(self, config):
        """
        Called upon CKAN setup, will pass current configuration dict
        to the plugin to read custom options.
        """
        discourse_url = config.get('discourse.url', None)
        discourse_username = config.get('discourse.username', None)
        discourse_count_cache_age = config.get('discourse.count_cache_age', 60)
        discourse_ckan_category = config.get('discourse.ckan_category', None)
        discourse_debug = asbool(config.get('discourse.debug', False))
        discourse_api_key = config.get('discourse.api_key', '')
        discourse_category_id = config.get('discourse.category_id', '')
        discourse_metadata_fields = config.get('discourse.metadata_fields', '').split()

        if discourse_url is None:
            log.warn("No discourse forum name is set. Please set \
            'discourse.url' in your .ini!")
        else:
            discourse_url = discourse_url.rstrip('/') + '/'

        if discourse_ckan_category is None:
            log.warn("Discourse needs discourse.ckan_category set to work. Please set \
            'discourse.ckan_category' in your .ini!")

        # check for valid JSON
        category_url = discourse_url + discourse_ckan_category + '.json'
        try:
            headers = {
                'Content-Type': 'multipart/form-data;',
                'Api-Key': discourse_api_key,
                'Api-Username': discourse_username
            }
            r = requests.get(category_url, headers=headers, verify=False)
            test_category_dict = r.json()
        except:
            log.warn(category_url + " is not a valid Discourse JSON endpoint!")

        config['pylons.app_globals'].has_commenting = True

        # store these so available to class methods
        self.__class__.discourse_url = discourse_url
        self.__class__.discourse_username = discourse_username
        self.__class__.discourse_count_cache_age = discourse_count_cache_age
        self.__class__.discourse_ckan_category = discourse_ckan_category
        self.__class__.discourse_debug = discourse_debug
        self.__class__.next_sync = time.time() + discourse_count_cache_age
        self.__class__.topic_lookup_dict = {}
        self.__class__.active_conversations = 0
        self.__class__.discourse_sync()

        self.discourse_category_id = discourse_category_id
        self.discourse_metadata_fields = discourse_metadata_fields

        self.discourse_api = DiscourseApi(
            discourse_url,
            discourse_username,
            discourse_api_key
        )

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'discourse')


    @classmethod
    def discourse_sync(cls):
        """
        retrieves comment counts from discourse
        caches results for 60 seconds by default
        """

        if time.time() < cls.next_sync and len(cls.topic_lookup_dict.keys()) > 0:
            return cls.active_conversations

        topic_lookup_dict = dict()

        try:
            category_url = cls.discourse_url + cls.discourse_ckan_category + '.json'
            headers = {
                'Content-Type': 'multipart/form-data;',
                'Api-Key': cls.discourse_api_key,
                'Api-Username': cls.discourse_username
            }
            r = requests.get(category_url, headers=headers, verify=False)
            category_dict = r.json()
            topics_dict = category_dict['topic_list']['topics']
            cls.active_conversations = 0

            for topic in topics_dict:
                topic_title = topic['title']
                if topic['posts_count'] > 1:
                    cls.active_conversations += 1
                    topic_lookup_dict[topic_title] = topic['posts_count']

            while 'more_topics_url' in category_dict['topic_list']:
                more_url = cls.discourse_url + category_dict['topic_list']['more_topics_url']
                more_url = more_url.replace("?category_id", ".json?category_id")
                headers = {
                    'Content-Type': 'multipart/form-data;',
                    'Api-Key': cls.discourse_api_key,
                    'Api-Username': cls.discourse_username
                }
                r = requests.get(more_url, headers=headers, verify=False)
                category_dict = r.json()
                topics_dict = category_dict['topic_list']['topics']

                for topic in topics_dict:
                    topic_title = topic['title']
                    if topic['posts_count'] > 1:
                        cls.active_conversations += 1
                        topic_lookup_dict[topic_title] = topic['posts_count']

            cls.next_sync = time.time() + cls.discourse_count_cache_age
        except:
            # dont try again immediately, next sync attempt at least 60 seconds from now
            cls.next_sync = time.time() + 60

        cls.topic_lookup_dict = topic_lookup_dict
        return cls.active_conversations


    @classmethod
    def discourse_comments(cls, canonical_url = ''):
        ''' Adds Discourse comments to the page.'''
        # we need to create a topic_id
        c = plugins.toolkit.c
        pkg_dict = {}

        if not canonical_url:
            try:
                topic_id = c.controller
                if topic_id == 'package':
                    topic_id = 'dataset'

                pkg_dict = plugins.toolkit.c.__getattr__("pkg_dict")

                # we do this so we always tie the same comment even if the url is canonical hash
                # or human-readable version.  This is necessary since the CKAN RSS feed uses hash
                # resulting in duplicate discourse topics for the same dataset
                topic_id += '/' + pkg_dict["name"]

                # Only create topics for publicly available CKAN URLs
                if pkg_dict["private"]:
                    topic_id = ''

                if c.action == 'resource_read':
                    topic_id = 'dataset-resource::' + c.resource_id
            except:
                topic_id = ''

            if topic_id:
                discourse_topic = g.site_url.rstrip('/') + '/' + topic_id
            else:
                return ''
        else:
            discourse_topic = canonical_url

        # ignore locale settings
        lang_code = pylons.request.environ['CKAN_LANG']

        monolingualURL = re.match('(http://.*?/)('+ lang_code +')/(.*)$', discourse_topic)
        if monolingualURL is not None:
            # we strip language code from URL
            discourse_topic = monolingualURL.group(1) + monolingualURL.group(3)
        else:
            monolingualURL = re.match('(http://.*?/)(..)/(.*)$', discourse_topic)
            if monolingualURL is not None:
                discourse_topic = monolingualURL.group(1) + monolingualURL.group(3)

        data = {'topic_id' : discourse_topic,
            'discourse_url' : cls.discourse_url,
            'discourse_username' : cls.discourse_username }

        for plugin in p.PluginImplementations(IDiscourse):
            data = plugin.before_render_comments(data, pkg_dict)

        if cls.discourse_debug:
            data['pkg_dict'] = json.dumps(pkg_dict, indent=3)
            comments_snippet = 'discourse_comments_debug.html'
        else:
            comments_snippet = 'discourse_comments.html'
        return plugins.toolkit.render_snippet(comments_snippet, data)

    @classmethod
    def discourse_latest(cls, num_comments=5):
        ''' Adds Discourse latest comments to the page. '''
        discourse_latest_feed = feedparser.parse(cls.discourse_url + 'latest.rss')
        data = {'discourse_latest_feed': discourse_latest_feed,
            'discourse_num_comments' : num_comments}
        return plugins.toolkit.render_snippet('discourse_latest.html', data)

    @classmethod
    def discourse_comments_count(cls, topic_id):
        ''' Adds Discourse comment counts for a given Discourse topic '''
        num_comments = cls.topic_lookup_dict.get(topic_id, 1) - 1
        return num_comments

    @classmethod
    def discourse_category_url(cls):
        ''' returns Discourse CKAN category URL  '''
        return cls.discourse_url + cls.discourse_ckan_category

    def get_helpers(self):
        return {'discourse_comments' : self.discourse_comments,
                'discourse_latest' : self.discourse_latest,
                'discourse_comments_count' : self.discourse_comments_count,
                'discourse_sync' : self.discourse_sync,
                'discourse_category_url' : self.discourse_category_url}

    # IPackageController

    # After a dataset is created a new topic in discourse should be made with dataset metadata
    def after_create(self, context, pkg_dict):
        if not pkg_dict.get('private'):
            jobs.enqueue(self.create_discourse_topic, [pkg_dict])
        return

    # After a dataset is updated the first post in the discourse topic should be updated with new dataset metadata
    def after_update(self, context, pkg_dict):
        if not pkg_dict.get('private'):
            jobs.enqueue(self.update_discourse_topic, [pkg_dict])
        return

    def create_discourse_topic(self, pkg_dict):
        title = pkg_dict.get('title')
        raw = self.create_topic_raw(pkg_dict)
        log.info('Create discourse topic: {0}'.format(title))
        self.discourse_api.create_topic(title, raw, self.discourse_category_id)
        return

    def update_discourse_topic(self, pkg_dict):
        topic_list = self.discourse_api.get_topic_list(self.discourse_category_id)
        for topic in topic_list:
            if topic.get('title') == pkg_dict.get('title'):
                topic_id = topic.get('id')
                topic_posts = self.discourse_api.get_topic_posts(topic_id)
                raw = self.create_topic_raw(pkg_dict)
                for post in topic_posts:
                    if post.get('post_number') == 1:
                        cooked = post.get('cooked', '').replace(' rel="nofollow noopener"', '')
                        if cooked != raw:
                            log.info('Update discourse topic post: {0}'.format(topic.get('title')))
                            self.discourse_api.update_post(post.get('id'), raw)
                        break
                break
        return

    # Create the raw html used in posts
    def create_topic_raw(self, pkg_dict):
        full_package = get_action('package_show')({}, {'id': pkg_dict.get('id')})
        organization = full_package.get('organization', {})
        groups = full_package.get('groups', [])
        tags = full_package.get('tags', [])
        resources = full_package.get('resources', {})

        title = pkg_dict.get('title') or pkg_dict['name']
        site_url = config.get('ckan.site_url')
        pkg_url = '{0}/dataset/{1}'.format(site_url, pkg_dict['name'].encode("utf-8"))

        raw = '<h2>{0}</h2>'.format(title.encode("utf-8"))

        if pkg_dict.get('notes'):
            raw += '<p>{0}</p>'.format(pkg_dict.get('notes').encode("utf-8"))

        raw += '<p>'
        # Add organization title to raw
        if organization.get('title'):
            raw += '<strong>Publisher</strong>: {0}<br>'.format(organization.get('title').encode("utf-8"))

        # Get metadata for fields defined in ini config and use display labels
        if self.discourse_metadata_fields:
            schema_fields = self.get_schema_fields()
            for field in self.discourse_metadata_fields:
                if pkg_dict.get(field):
                    label = field
                    for item in schema_fields:
                        if item.get('field_name') == field:
                            label = item.get('label')
                            break
                    raw += '<strong>{0}</strong>: {1}<br>'.format(label, pkg_dict.get(field).encode("utf-8"))
        raw += '</p>'

        raw += '<p>'
        if groups:
            group_list = []
            for group in groups:
                if group.get('title') not in group_list:
                    group_list.append(group.get('title'))
            group_alias = str(config.get('ckan.group_alias', 'Group'))
            raw += '<strong>{0}</strong>: {1}<br>'.format(group_alias, ', '.join(group_list).encode("utf-8"))

        if tags:
            tag_list = []
            for tag in tags:
                if tag.get('name') not in tag_list:
                    tag_list.append(tag.get('name'))
            raw += '<strong>Tags</strong>: {0}'.format(', '.join(tag_list).encode("utf-8"))
        raw += '</p>'

        raw += '<p>See this dataset on the Data Portal:<br><a href="{0}">{0}</a></p>'.format(pkg_url)

        if resources:
            raw += '<p>Included resources:<br>'
            for res in resources:
                if res.get('id'):
                    res_url = '{0}/resource/{1}'.format(pkg_url, res.get('id'))
                    raw += '<a href="{0}">{1}</a><br>'.format(res_url, res.get('name', 'Unnamed resource').encode("utf-8"))
            raw += '</p>'

        return raw

    # Get the display labels for metadata fields
    # Custom schemas will have different labels
    def get_schema_fields(self):
        try:
            schema_fields = get_action('scheming_dataset_schema_show')({},{'type':'dataset'})
            return schema_fields['dataset_fields']
        except:
            schema_fields = [
                {"field_name": "title", "label": "Title"},
                {"field_name": "name", "label": "Dataset ID"},
                {"field_name": "notes", "label": "Description"},
                {"field_name": "tag_string", "label": "Tags"},
                {"field_name": "license_id", "label": "License"},
                {"field_name": "owner_org", "label": "Organization"},
                {"field_name": "group", "label": "Groups"},
                {"field_name": "url", "label": "Source"},
                {"field_name": "version", "label": "Version"},
                {"field_name": "author", "label": "Author"},
                {"field_name": "author_email", "label": "Author Email"},
                {"field_name": "maintainer", "label": "Maintainer"},
                {"field_name": "maintainer_email", "label": "Maintainer Email"}
            ]
        return schema_fields
