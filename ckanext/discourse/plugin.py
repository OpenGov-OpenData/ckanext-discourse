import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests
import time
import sys
import re
import pylons
import json
from ckan.plugins.toolkit import asbool
from ckan.common import g

import logging

log = logging.getLogger(__name__)


class DiscoursePlugin(plugins.SingletonPlugin):
    """
    Insert javascript fragments into package pages and the home page to
    allow users to view and create comments on any package.
    """
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    def configure(self, config):
        """
        Called upon CKAN setup, will pass current configuration dict
        to the plugin to read custom options.
        """
        discourse_url = config.get('discourse.url', None)
        discourse_username = config.get('discourse.username', None)
        discourse_count_cache_age = config.get('discourse.count_cache_age', 300)
        discourse_ckan_category = config.get('discourse.ckan_category', None)
        discourse_debug = asbool(config.get('discourse.debug', False))

        if discourse_url is None:
            log.warn("No discourse forum name is set. Please set \
            'discourse.url' in your .ini!")
        else:
            discourse_url = discourse_url.rstrip('/') + '/'

        if discourse_ckan_category is None:
            log.warn("Discourse needs discourse.ckan_category set to work. Please set \
            'discourse.ckan_category' in your .ini!")
        elif not discourse_ckan_category.lower().endswith('.json'):
            discourse_ckan_category += '.json'

        # check for valid JSON
        try:
            discourse_api = discourse_url + discourse_ckan_category
            r = requests.get(discourse_api, verify=False)
            test_category_dict = r.json()
        except:
            log.warn(discouse_api + " is not a valid Discourse JSON endpoint!")

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
            r = requests.get(cls.discourse_url + cls.discourse_ckan_category, verify=False)
            category_dict = r.json()
            topics_dict = category_dict['topic_list']['topics']
            cls.active_conversations = 0

            for topic in topics_dict:
                topic_title = topic['title'][:-len(g.site_title)].strip() if topic['title'].endswith(g.site_title) else topic['title']
                if topic['posts_count'] > 1:
                    cls.active_conversations += 1
                    topic_lookup_dict[topic_title] = topic['posts_count']

            while 'more_topics_url' in category_dict['topic_list']:
                more_url = cls.discourse_url + category_dict['topic_list']['more_topics_url']
                more_url = more_url.replace("?category_id", ".json?category_id")
                r = requests.get(more_url, verify=False)
                category_dict = r.json()
                topics_dict = category_dict['topic_list']['topics']

                for topic in topics_dict:
                    topic_title = topic['title'][:-len(g.site_title)].strip() if topic['title'].endswith(g.site_title) else topic['title']
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

    def get_helpers(self):
        return {'discourse_comments' : self.discourse_comments,
                'discourse_latest' : self.discourse_latest,
                'discourse_comments_count' : self.discourse_comments_count,
                'discourse_sync' : self.discourse_sync}
