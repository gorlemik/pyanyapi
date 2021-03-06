# coding: utf-8
"""
Classes for fabrics of interfaces.
Generates interfaces dynamically from given settings.
"""
from .interfaces import (
    XPathInterface,
    XMLInterface,
    XMLObjectifyInterface,
    JSONInterface,
    RegExpInterface,
    CombinedInterface
)
from .helpers import attach_attribute, attach_cached_property


class BaseParser(object):
    """
    Fabric for some API-like components, which supposes to provide interface to different types of content.
    """
    interface_class = None

    def __init__(self, settings=None):
        parents_settings = self.get_parents_settings()
        if settings:
            parents_settings.update(settings)
        self.settings = parents_settings

    @property
    def attributes(self):
        extra_attributes = []
        for name in dir(self):
            if name == 'attributes':
                continue
            attr = getattr(self, name)
            if hasattr(attr, '_interface_property') or hasattr(attr, '_interface_method'):
                extra_attributes.append(name)
        return list(self.settings.keys()) + extra_attributes

    def get_parents_settings(self):
        """
        Gather settings from parent classes. It provides some kind of settings inheritance.
        """
        parents_settings = {}
        for klass in reversed(self.__class__.mro()):
            parents_settings.update(getattr(klass, 'settings', {}))
        return parents_settings

    def parse(self, content=''):
        """
        Generates new class instance with desired attributes.
        """
        self.content = self.prepare_content(content)

        class Interface(self.interface_class):
            pass

        self.setup_class(Interface)

        init_kwargs = self.get_interface_kwargs()

        return Interface(**init_kwargs)

    def get_interface_kwargs(self):
        return {'content': self.content}

    def prepare_content(self, content):
        """
        Hook to provide way to transform content.
        """
        return content

    def setup_class(self, cls):
        """
        Attaches dynamic properties & methods.
        """
        self.process_settings(cls)
        self.process_decorators(cls)

    def process_settings(self, cls):
        """
        Generates methods, based on settings.
        """
        for name, settings in self.settings.items():
            attr = cls.init_attr(settings)
            attach_cached_property(cls, name, attr)

    def process_decorators(self, cls):
        """
        Re-attach all attributes, which is decorated with
        @interface_property or @interface_method decorators to new class.
        """
        for name in dir(self):
            attr = getattr(self, name)
            if getattr(attr, '_interface_property', False):
                attach_cached_property(cls, name, attr)
            elif getattr(attr, '_interface_method', False):
                attach_attribute(cls, name, attr)

    def __and__(self, other):
        return CombinedParser(self, other)


class CombinedParser(BaseParser):
    """
    Combines multiple parsers in one. Its can be different types also.
    """
    interface_class = CombinedInterface

    def __init__(self, *parsers, **kwargs):
        if parsers:
            self.parsers = parsers
        super(CombinedParser, self).__init__(**kwargs)

    @property
    def attributes(self):
        return super(CombinedParser, self).attributes + sum([parser.attributes for parser in self.parsers], [])

    def get_interface_kwargs(self):
        kwargs = super(CombinedParser, self).get_interface_kwargs()
        kwargs['parsers'] = self.parsers
        return kwargs


class HTMLParser(BaseParser):
    interface_class = XPathInterface


class XMLParser(BaseParser):
    interface_class = XMLInterface

    def prepare_content(self, content):
        return content.replace('encoding="UTF-8"', '').replace('encoding="utf-8"', '')


class XMLObjectifyParser(BaseParser):
    interface_class = XMLObjectifyInterface


class JSONParser(BaseParser):
    interface_class = JSONInterface


class RegExpParser(BaseParser):
    interface_class = RegExpInterface
