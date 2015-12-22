# Copyright ClusterHQ Inc.  See LICENSE file for details.

"""
Tests for AWS CloudFormation installer.
"""

import os

from twisted.internet import reactor
from twisted.internet.defer import maybeDeferred

from ...common.runner import run_ssh
from ...common import gather_deferreds
from ...testtools import AsyncTestCase

CLIENT_IP = os.environ['CLIENT_IP']
DOCKER_HOST = os.environ['DOCKER_HOST']
NODE0 = os.environ['CLUSTER_NODE0']
NODE1 = os.environ['CLUSTER_NODE1']
COMPOSE_NODE0 = '/home/ubuntu/postgres/docker-compose-node0.yml'
COMPOSE_NODE1 = '/home/ubuntu/postgres/docker-compose-node1.yml'


def remote_docker_compose(compose_file_path, *args):
    docker_compose_output = []
    d = run_ssh(
        reactor,
        'ubuntu',
        CLIENT_IP,
        ('DOCKER_HOST={}'.format(DOCKER_HOST),
         'docker-compose', '--file', compose_file_path) + args,
        handle_stdout=docker_compose_output.append
    )
    d.addCallback(
        lambda process_result: (process_result, docker_compose_output)
    )
    return d


def remote_postgres(host, command):
    postgres_output = []
    d = run_ssh(
        reactor,
        'ubuntu',
        CLIENT_IP,
        ('psql', '-h ' + host,
         '--user=flocker', '--password=flocker',
         '--execute={}'.format(command)),
        handle_stdout=postgres_output.append
    )
    d.addCallback(
        lambda process_result: (process_result, postgres_output)
    )
    return d


class DockerComposeTests(AsyncTestCase):
    """
    Tests for AWS CloudFormation installer.
    """

    def setUp(self):
        d = maybeDeferred(super(DockerComposeTests, self).setUp)

        def local_setup(ignored):
            d_node1 = remote_docker_compose(COMPOSE_NODE0, 'stop')
            d_node1.addCallback(
                lambda ignored: remote_docker_compose(
                    COMPOSE_NODE0, 'rm', '-f'
                )
            )

            d_node2 = remote_docker_compose(COMPOSE_NODE1, 'stop')
            d_node2.addCallback(
                lambda ignored: remote_docker_compose(
                    COMPOSE_NODE1, 'rm', '-f'
                )
            )
            return gather_deferreds([d_node1, d_node2])
        d.addCallback(local_setup)
        return d

    def test_docker_compose_up_postgres(self):
        """
        """
        database_name = 'test_docker_compose_up_postgres'
        d = remote_docker_compose(COMPOSE_NODE0, 'up', '-d')

        d.addCallback(
            lambda ignored: remote_postgres(
                NODE0, 'create database {}'.format(database_name)
            )
        )

        d.addCallback(
            lambda ignored: remote_docker_compose(COMPOSE_NODE0, 'stop')
        )

        d.addCallback(
            lambda ignored: remote_docker_compose(
                COMPOSE_NODE0, 'rm', '--force'
            )
        )

        d = remote_docker_compose(COMPOSE_NODE1, 'up', '-d')

        d.addCallback(
            lambda ignored: remote_postgres(
                NODE1, 'show databases'
            )
        )

        d.addCallback(
            lambda (process_status, process_output): self.assertEqual(
                "", process_output
            )
        )

        return d
