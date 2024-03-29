"""
Launch an image with a temporary user via JupyterHub
"""
import base64
import json
import random
import re
import string
from urllib.parse import urlparse
import uuid
import os

from tornado.log import app_log
from tornado import web, gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from traitlets.config import LoggingConfigurable
from traitlets import Integer, Unicode, Bool


class Launcher():

    retry_delay = 20
    retries = 100
    hub_url = "127.0.0.1:8000/"
    server_name = 'voila'

    def __init__(self, user, auth):
        print('TOKEN?', auth)
        self.hub_api_token = auth
        self.user = user

    def log(self, *args):
        print("***LOG MSG***:", args)

    async def api_request(self, url, *args, **kwargs):
        """Make an API request to JupyterHub"""
        headers = kwargs.setdefault('headers', {})
        headers.update({'Authorization': 'token %s' % self.hub_api_token})
        hub_api_url = os.getenv('JUPYTERHUB_API_URL', '') or self.hub_url + 'hub/api'
        if not hub_api_url.endswith('/'):
            hub_api_url = hub_api_url + '/'
        request_url = hub_api_url + url
        req = HTTPRequest(request_url, *args, **kwargs)
        self.log('##REquest##', request_url, *args, kwargs.items())
        retry_delay = self.retry_delay
        for i in range(1, self.retries + 1):
            try:
                return await AsyncHTTPClient().fetch(req)
            except HTTPError as e:
                # swallow 409 errors on retry only (not first attempt)
                if i > 1 and e.code == 409 and e.response:
                    self.log("Treating 409 conflict on retry as success")
                    return e.response
                # retry requests that fail with error codes greater than 500
                # because they are likely intermittent issues in the cluster
                # e.g. 502,504 due to ingress issues or Hub relocating,
                # 599 due to connection issues such as Hub restarting
                if e.code >= 500:
                    self.log("Error accessing Hub API (using %s): %s", request_url, e)
                    if i == self.retries:
                        # last api request failed, raise the exception
                        raise
                    await gen.sleep(retry_delay)
                    # exponential backoff for consecutive failures
                    retry_delay *= 2
                else:
                    raise

    async def get_user_data(self):
        resp = await self.api_request(
            'users/%s' % self.user['name'],
            method='GET',
        )
        body = json.loads(resp.body.decode('utf-8'))
        return body

    async def launch(self, image):
        """Launch a server for a given image
        - creates a temporary user on the Hub if authentication is not enabled
        - spawns a server for temporary/authenticated user
        - generates a token
        - returns a dict containing:
          - `url`: the URL of the server
          - `image`: image spec
          - `token`: the token for the server
        """

        username = self.user['name']
        # TODO: validate the image argument?

        # data to be passed into spawner's user_options during launch
        # and also to be returned into 'ready' state
        data = {'image': image,
                'token': base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=\n')}

        # server name to be used in logs
        _server_name = " {}".format(self.server_name)

        # # test if exists and early exit if so
        user_data = await self.get_user_data()
        started_server = user_data['servers'].get(self.server_name, None)
        if started_server and started_server['ready']:
            redirect_url = started_server['url']
            return {'status': 'running', 'url': redirect_url}

        # start server
        app_log.info("Starting server%s for user %s with image %s", _server_name, username, image)
        try:
            resp = await self.api_request(
                'users/{}/servers/{}'.format(username, self.server_name),
                method='POST',
                body=json.dumps(data).encode('utf8'),
            )

            if resp.code == 202:
                # Server hasn't actually started yet
                # We wait for it!
                # NOTE: This ends up being about ten minutes
                for i in range(64):
                    user_data = await self.get_user_data()
                    print('***Started... userdata:***:', user_data['servers'][self.server_name])

                    if user_data['servers'][self.server_name]['ready']:
                        # exit, server running
                        return {'status': 'running', 'url': user_data['servers'][self.server_name]['url']}

                    if user_data['servers'][self.server_name]['progress_url']:
                        # exit, server pending with progress url
                        return {'url': user_data['servers'][self.server_name]['progress_url'],
                                'status': 'pending'}

                    if not user_data['servers'][self.server_name]['pending']:
                        raise web.HTTPError(500, "Image %s for user %s failed to launch" % (image, username))
                    # FIXME: make this configurable
                    # FIXME: Measure how long it takes for servers to start
                    # and tune this appropriately
                    await gen.sleep(min(1.4 ** i, 10))
                else:
                    raise web.HTTPError(500, "Image %s for user %s took too long to launch" % (image, username))

        except HTTPError as e:
            if e.response:
                body = e.response.body
            else:
                body = ''

            app_log.error("Error starting server{} for user {}: {}\n{}".
                          format(_server_name, username, e, body))
            raise web.HTTPError(500, "Failed to launch image %s" % image)

        return {'url': '/user/%s/%s' % (username, self.server_name), 'status': 'running'}
