"""Auto-tagging module for Pulumi."""

import pulumi

from .taggable import is_taggable


def register_auto_tags(auto_tags):
    """Register a global stack transformation that merges a set of tags with resource definitions."""
    return pulumi.runtime.register_stack_transformation(lambda args: auto_tag(args, auto_tags))


def auto_tag(args, auto_tags):
    """Apply the given tags to the resource properties if applicable."""
    if is_taggable(args.type_):
        args.props["tags"] = {**(args.props["tags"] or {}), **auto_tags}
    return pulumi.ResourceTransformationResult(args.props, args.opts)
