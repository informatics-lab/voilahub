"""An example service authenticating with the Hub.
This serves `/services/whoami/`, authenticated with the Hub, showing the user their own info.
"""
import json
import os
from getpass import getuser
from urllib.parse import urlparse, quote as urlquote

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.web import authenticated
from tornado.web import RequestHandler

from jupyterhub.services.auth import HubAuthenticated

from .launcher import Launcher


HubAuthenticated.hub_auth


class VoilaDashboardsGetSettings(HubAuthenticated, RequestHandler):
    @authenticated
    def get(self):
        user_model = self.get_current_user()
        self.set_header('content-type', 'application/json')
        self.write(json.dumps({
            'public_share': os.environ['VOILA_HUB_PUBLIC_SHARE']
        }))


class VoilaDashboardsLaunch(HubAuthenticated, RequestHandler):
    @authenticated
    async def get(self, image, notebook):
        launcher = Launcher(self.get_current_user(), self.hub_auth.api_token)
        result = await launcher.launch('image')

        print("### RESULT ###:", result)

        if result['status'] == 'running':
            redirect_url = f"{result['url']}/voila/render/{notebook}"
        if result['status'] == 'pending':
            redirect_url = f"{result['url']}?next={urlquote('/voila/render/' + notebook)}"

        redirect_url = redirect_url if redirect_url.startswith('/') else '/'+redirect_url

        print("### REDIRECT to###:", redirect_url)
        self.redirect(redirect_url)


def main():
    app = Application(
        [
            (os.environ['JUPYTERHUB_SERVICE_PREFIX'] + 'system/?', VoilaDashboardsGetSettings),
            (os.environ['JUPYTERHUB_SERVICE_PREFIX'] + r'launch/([^/]*)/(.*)', VoilaDashboardsLaunch)
        ]
    )

    http_server = HTTPServer(app)
    url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])

    http_server.listen(url.port, url.hostname)

    IOLoop.current().start()


main()
