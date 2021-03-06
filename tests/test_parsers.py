# coding: utf-8
import pytest

from ._compat import patch
from .conftest import ChildParser
from pyanyapi import XMLObjectifyParser, XMLParser, JSONParser, HTMLParser
from pyanyapi.exceptions import ResponseParseError


def test_xml_objectify_parser():
    parsed = XMLObjectifyParser().parse('<xml><test>123</test></xml>')
    assert parsed.test == 123
    assert parsed.not_existing is None


def test_xml_objectify_parser_error():
    parsed = XMLObjectifyParser().parse('<xml><test>123')
    with pytest.raises(ResponseParseError):
        parsed.test


def test_xml_parser_error():
    parsed = XMLParser({'test': None}).parse('<xml><test>123')
    with pytest.raises(ResponseParseError):
        parsed.test


def test_xml_parsed():
    content = '''<?xml version="1.0" encoding="UTF-8"?>
    <response>
    <id>32e9a4a2</id>
    <test-mode>1</test-mode>
    <type>accept</type>
    </response>
    '''
    parser = XMLParser({
        'success': {
            'base': '//test-mode/text()'
        }
    })
    assert parser.parse(content).success == ['1']
    assert parser.parse(content).parse('string(//id/text())') == '32e9a4a2'


def test_json_parsed():
    content = '''
    {
        "container":
        {
            "id": 1138003,
            "inner":
            [
                {
                    "end": {
                        "id": 123
                    }
                }
            ]
        }
    }
    '''

    parser = JSONParser({
        'success': {
            'base': 'container > inner > 0 > end > id'
        }
    })
    assert parser.parse(content).success == 123
    parser = JSONParser({
        'success': {
            'base': 'container > inner',
            'children': 'end > id',
        }
    })
    assert parser.parse(content).success == [123]


JSON_CONTENT = '{"container":{"test":"value"}}'


def test_multiple_parser_join():
    first_parser = HTMLParser({
        'test': {'base': 'string(//a/@href)'}
    })
    second_parser = JSONParser({
        'success': {
            'base': 'container > test',
        }
    })
    html_content = "<html><body><a href='#test'></body></html>"
    for result_parser in ((first_parser & second_parser), (second_parser & first_parser)):
        assert result_parser.parse(html_content).test == '#test'
        assert result_parser.parse(JSON_CONTENT).success == 'value'
    third_parser = JSONParser({
        'fail': {
            'base': 'container > test',
        }
    })
    result_parser = first_parser & second_parser & third_parser
    assert result_parser.parse(JSON_CONTENT).success == 'value'


def test_multiply_parsers_declaration(dummy_parser):
    parsed = dummy_parser.parse(JSON_CONTENT)
    assert parsed.success == 'value'
    assert parsed.combined == '123-value'
    assert parsed.method('-123') == 'value-123'
    assert parsed.test is None

    parsed = dummy_parser.parse("<html><body><a href='#test'></body></html>")
    assert parsed.test == '#test'
    assert parsed.success is None


@pytest.mark.parametrize(
    'content, attr, expected',
    (
        ('{"container":{"test":"value"}}', 'test', 'value'),
        ('{"container":{"test":"value"}}', 'second', None),
        ('{"container":{"fail":[1]}}', 'second', None),
        ('{"container":[[1],[],[3]]}', 'third', [1, None, 3]),
        ('{"container":null}', 'null', None),
        ('{"container":[1,2]}', 'test', '1,2'),
    )
)
def test_empty_values(empty_values_parser, content, attr, expected):
    parsed = empty_values_parser.parse(content)
    assert getattr(parsed, attr) == expected


def test_attributes(empty_values_parser):
    assert set(empty_values_parser.attributes) == set(['combined', 'test', 'test', 'second', 'null', 'third'])


def test_efficient_parsing(empty_values_parser):
    with patch.object(empty_values_parser.parsers[0], 'parse') as regexp_parser:
        assert empty_values_parser.parse(JSON_CONTENT).second is None
        assert not regexp_parser.called


def test_simple_config_xml_parser():
    parsed = XMLParser({'test': 'string(//test/text())'}).parse('<xml><test>123</test></xml>')
    assert parsed.test == '123'


def test_simple_config_json_parser():
    parsed = JSONParser({'test': 'container > test'}).parse(JSON_CONTENT)
    assert parsed.test == 'value'


def test_settings_inheritance():
    parser = ChildParser({'child2': 'override'})
    assert parser.settings['child2'] == 'override'
    assert parser.settings['child1'] == 'test3'
    assert parser.settings['parent2'] == 'child_override'
    assert parser.settings['parent1'] == 'test1'


def test_complex_config():
    parsed = XMLParser({'test': {'base': '//test', 'children': 'text()|*//text()'}}).parse(
        '<xml><test>123 </test><test><inside> 234</inside></test></xml>'
    )
    assert parsed.test == ['123', '234']
