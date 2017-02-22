# Copyright (C) IBM Corp. 2016.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import os
import sys

import yaml

from lib import log_helper
from lib import utils

LOG_FILE_NAME = 'builds.log'
BUILD_REPO_ARGS = {
    ('--packages-metadata-repo-url',):
        dict(help='Packages metadata git repository URL'),
    ('--packages-metadata-repo-branch',):
        dict(help='Packages metadata git repository branch'),
    ('--http-proxy',):
        dict(help='HTTP proxy URL'),
}
PACKAGE_ARGS = {
    ('--packages', '-p'):
        dict(help='Packages to be built',
             nargs='*'),
}
PACKAGE_BUILD_ARGS = {
    ('--keep-build-dir',):
        dict(help='Keep build directory and its logs and artifacts.',
             action='store_true'),
    ('--force-rebuild',):
        dict(help='Force the rebuild of packages. The default is to only '
             'build packages when they have updated files since the last '
             'build results.',
             action='store_true'),
}
DISTRO_ARGS = {
    ('--distro-name',):
        dict(help='Base Linux distribution'),
    ('--distro-version',):
        dict(help='Base Linux distribution version')
}
MOCK_ARGS = {
    ('--mock-binary',):
        dict(help='Mock binary path', default='/usr/bin/mock'),
    ('--mock-config',):
        dict(help='Mock config file'),
    ('--mock-args',):
        dict(help='Arguments passed to mock command', default=''),
}
RELEASE_NOTES_ARGS = {
    ('--release-notes-repo-url',):
        dict(help='Release notes repository URL'),
    ('--release-notes-repo-branch',):
        dict(help='Branch of the release notes repository to checkout'),
}
PUSH_REPO_ARGS = {
    ('--no-commit-updates',):
        dict(help='Commit file updates to local repository', action='store_false',
             dest='commit_updates'),
    ('--no-push-updates',):
        dict(help='Push file updates to remote repository', action='store_false',
             dest='push_updates'),
    ('--push-repo-url',):
        dict(help='URL of the repository used for pushing'),
    ('--push-repo-branch',):
        dict(help='Branch of the repository used for pushing',
             default='master'),
    ('--updater-name',):
        dict(help='Name used when updating RPM specification files change logs '
             'and creating git commits'),
    ('--updater-email',):
        dict(help='Email used when updating RPM specification files change logs '
             'and creating git commits'),
}
BUILD_ARGS = {
    ('--result-dir', '-r'):
        dict(help='Directory to save the RPMs.',
             default='result'),
}
ISO_ARGS = {
    ('--packages-dir', '-d'):
        dict(help='Directory of packages used in the ISO image.',
             default='result/packages/latest'),
    ('--iso-name',):
        dict(help='ISO name.',
             default='OpenPOWER-Host_OS'),
    ('--log-file',):
        dict(help='ISO creation log file path.',
             default='/var/log/host-os/iso.log'),
    ('--automated-install-file',):
        dict(help='Path of a kickstart file, used to automate the installation of a RPM-based Linux distribution',
             default='host-os.ks'),
    ('--hostos-packages-groups',):
        dict(help='Packages groups in yum repository'),
    ('--automated-install-packages-groups',):
        dict(help='Packages and packages groups which are installed using automated installation', nargs='*'),
    ('--mock-iso-repo-name',):
        dict(help='Name of the yum repository, to create from OpenPOWER Host OS packages'),
    ('--mock-iso-repo-dir',):
        dict(help='Directory path of the yum repository, to create from OpenPOWER Host OS packages'),
    ('--distro-repos-urls',):
        dict(help='Base Linux distribution yum repositories URLs'),
}
SUBCOMMANDS = [
    ('build-packages', 'Build packages.',
        [PACKAGE_ARGS, PACKAGE_BUILD_ARGS, MOCK_ARGS, DISTRO_ARGS, BUILD_REPO_ARGS, BUILD_ARGS]),
    ('build-release-notes', 'Create release notes',
        [RELEASE_NOTES_ARGS, PUSH_REPO_ARGS, DISTRO_ARGS, BUILD_REPO_ARGS]),
    ('upgrade-versions', 'Upgrade packages versions',
        [PACKAGE_ARGS, PUSH_REPO_ARGS, DISTRO_ARGS, BUILD_REPO_ARGS]),
    ('update-versions-readme', 'Update the supported software versions table',
        [PUSH_REPO_ARGS, DISTRO_ARGS, BUILD_REPO_ARGS]),
    ('build-iso', 'Build ISO image',
        [ISO_ARGS, MOCK_ARGS, BUILD_ARGS]),
]


config_parser = None


def get_config():
    global config_parser
    if not config_parser:
        config_parser = ConfigParser()
        config_parser.parse()
    return config_parser


class ConfigParser(object):
    """
    Parses configuration options sources.

    Precedence is:
    cmdline > config file > argparse defaults
    """
    def __init__(self):
        # create the top-level parser
        self.parser = argparse.ArgumentParser()
        self._CONF = None
        self._setup_config_parser_options()

    @property
    def CONF(self):
        return self._CONF

    def _setup_config_parser_options(self):
        """
        Configures the argument parser object to match the expected
            configuration.
        """
        self.parser.add_argument('--config-file', '-c',
                                 help='Path of the configuration file for build '
                                      'scripts',
                                 # NOTE(maurosr): move this to /etc in the future
                                 default='./config.yaml')
        self.parser.add_argument('--verbose', '-v',
                                 help='Set the scripts to be verbose',
                                 action='store_true')
        self.parser.add_argument('--log-size',
                                 help='Size in bytes above which the log file '
                                 'should rotate', type=int, default=2<<20)
        self.parser.add_argument('--work-dir', '-w',
                                 help='Directory used to store all temporary '
                                 'files created during the process.',
                                 default='workspace')
        self._add_subparser()

    def _add_subparser(self):
        subparsers = self.parser.add_subparsers(
            dest="subcommand",
            help="Available subcommands")

        for command, help_msg, arg_groups in SUBCOMMANDS:
            parser_command = subparsers.add_parser(command, help=help_msg)
            for arg_group in arg_groups:
                for arg, options in arg_group.items():
                    parser_command.add_argument(*arg, **options)

    def parse_arguments_list(self, args):
        """
        Parses the arguments provided in the argument list and returns
            the result object.
        """
        result = self.parser.parse_args(args)
        return vars(result)

    def parse_config_file(self, config_file_path):
        """
        Parse the configuration file and return a dictionary containing the
            parsed values.
        """
        conf = {}
        with open(config_file_path) as stream:
            conf = yaml.safe_load(stream)
        return conf

    def parse(self):
        # parse the 'config-file' argument early so that we can use
        # the defaults defined in the config file to override the ones
        # in the 'add_argument' calls below.
        command_line_args = self.parser.parse_known_args()[0]
        config_file = command_line_args.config_file

        config = self.parse_config_file(config_file)
        self.parser.set_defaults(**config['common'])

        # Each subcommand may have a node for specific configurations
        # at the same level of the 'common' node
        COMMAND_TO_CONFIG_NODE = {
            "build-packages": "build_packages",
            "build-iso": "build_iso",
            "build-release-notes": "build_release_notes",
            "upgrade-versions": "upgrade_versions",
            "update-versions-readme": "update_versions_readme"
        }
        if command_line_args.subcommand in COMMAND_TO_CONFIG_NODE:
            # Override the default configurations with the ones specific
            # to the subcommand. This makes sure the specific
            # configurations are used instead of the generic ones, which
            # are already set above, avoiding conflicts on
            # configurations with the same name.
            node_name = COMMAND_TO_CONFIG_NODE[command_line_args.subcommand]
            self.parser.set_defaults(**config[node_name])

        args = self.parse_arguments_list(sys.argv[1:])

        # drop None values
        for key, value in args.items():
            if value is None:
                args.pop(key)

        # update node in config with subcommand args and then drop them from args
        if command_line_args.subcommand in COMMAND_TO_CONFIG_NODE:
            node_name = COMMAND_TO_CONFIG_NODE[command_line_args.subcommand]
            for key, value in args.items():
                if key in config[node_name]:
                    config[node_name][key] = value
                    args.pop(key)

        config['common'].update(args)
        self._CONF = config
        return config


def setup_default_config():
    """
    Setup the script environment. Parse configurations, setup logging
    and halt execution if anything fails.
    """
    try:
        CONF = get_config().CONF
    except OSError:
        print("Failed to parse settings")
        sys.exit(2)

    log_file_path = os.path.join(CONF.get('common').get('work_dir'),
                                 LOG_FILE_NAME)
    log_helper.LogHelper(log_file_path=log_file_path,
                         verbose=CONF.get('common').get('verbose'),
                         rotate_size=CONF.get('common').get('log_size'))

    proxy = CONF.get('common').get('http_proxy')
    if proxy:
        utils.set_http_proxy_env(proxy)

    return CONF
