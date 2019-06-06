import os
import sys


c.JupyterHub.authenticator_class = 'jupyterhub.auth.DummyAuthenticator'
c.JupyterHub.spawner_class = 'jupyterhub.spawner.SimpleLocalProcessSpawner'
c.JupyterHub.allow_named_servers = True
c.JupyterHub.services = [
    {
        'name': 'voilahub',
        'admin': True,
        'url': 'http://127.0.0.1:10101',
        'command': [sys.executable, '-m', 'voilahub.run'],
        'environment': {
            "VOILA_HUB_PUBLIC_SHARE": '/scratch/voila'
        }
    }
]
