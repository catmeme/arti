"""
Base provisioners for Pulumi.

This module provides base classes for Pulumi provisioners, including tagging and component resource utilities.
"""

import pulumi
from pulumi import get_project, get_stack
from pulumi_aws import get_caller_identity

from ..autotag import register_auto_tags
from ..util import get_package_info


class BaseTags:
    """Define and manage base tags for Pulumi resources."""

    def __init__(self, tags=None):
        """
        Initialize base tags with default values and optional additional tags.

        Args:
        - tags (dict): Optional additional tags to include.
        """
        caller_identity = get_caller_identity()
        package_info = get_package_info()
        pulumi_project = get_project()
        pulumi_stack = get_stack()

        self.tags = {
            "catmeme:created-by": caller_identity.arn,
            "catmeme:creation-method": "Pulumi",
            "catmeme:github:organization": package_info["github_org"],
            "catmeme:github:repository": package_info["github_repo"],
            "catmeme:pulumi:project": pulumi_project,
            "catmeme:pulumi:stack-name": pulumi_stack,
            "catmeme:pulumi:stack-version": package_info["version"],
        }

        if tags:
            self.tags.update(tags)

    def auto_tag(self) -> dict:
        """
        Register and return auto tags.

        Returns:
        - dict: Updated tags with auto tags registered.
        """
        self.tags = register_auto_tags(self.tags)
        return self.tags

    def get_tags(self) -> dict:
        """
        Retrieve the current set of tags.

        Returns:
        - dict: The current set of tags.
        """
        return self.tags


class BaseComponentResource(pulumi.ComponentResource):
    """Base component resource for Pulumi."""

    def __init__(self, name, args, opts=None):
        """
        Initialize the base component resource with a name and optional arguments and options.

        Args:
        - name (str): The name of the component resource.
        - args (dict): Arguments for the component resource.
        - opts (pulumi.ResourceOptions): Optional resource options.
        """
        super().__init__("custom:BaseComponentResource", name, args, opts)
        self.name = name

    def get_name(self):
        """
        Retrieve the name of the component resource.

        Returns:
        - str: The name of the component resource.
        """
        return self.name
