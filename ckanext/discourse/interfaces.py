from ckan.plugins.interfaces import Interface


class IDiscourse(Interface):

    def before_render_comments(self, data, pkg_dict):
        '''
        Called just before the discourse comments are rendered.

        It returns the data for the comments snippet.

        This extension point can be useful to alter the data before it is
        rendered, to prevent a display based on pkg_dict information or to
        even use a different user and/or discourse instance based on the
        pkg_dict.

        :param data: a dict containing ``topic_id``, ``discourse_url`` and 
                     ``discourse_username``
        :type data: dict
        :param pkg_dict: the information of the current dataset
        :type pkg_dict: dict


        :returns: A data dict containing the following keys:
                    * ``topic_id``: identifier of the topic on discourse,
                      provide an empty value to not display any topic
                    * ``discourse_url``: URL of the discourse instance
                    * ``discourse_username``: username of the discourse user
        :rtype: dict
        '''
        return data
