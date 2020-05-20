# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for module provides endpoints to calc cavs in bulk"""

import json

import ddt

from ggrc.models import all_models

from integration import ggrc
from integration.ggrc.models import factories


@ddt.ddt
class TestMatrix(ggrc.TestCase):
  """Test endpoint for cad group functionality"""

  ENDPOINT_URL = "/api/bulk_operations/cavs/search"

  def setUp(self):
    super(TestMatrix, self).setUp()
    self.client.get('/login')
    self.api = ggrc.Api()
    self.asmt1 = factories.AssessmentFactory(
        assessment_type="Control",
        sox_302_enabled=True,
    )
    self.query = [{
        "object_name": "Assessment",
        "type": "ids",
        "filters": {"expression": {}},
    }]

  @staticmethod
  def _get_text_payload():
    """Gets payload for text CAD.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "title": "CAD Text",
        "attribute_type": "Text",
        "definition_type": "Assessment",
    }

  @staticmethod
  def _get_rich_text_payload():
    """Gets payload for rich text CAD.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "title": "CAD Rich Text",
        "attribute_type": "Rich Text",
        "definition_type": "assessment",
    }

  @staticmethod
  def _get_date_payload():
    """Gets payload for date CAD.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "title": "CAD Date",
        "attribute_type": "Date",
        "definition_type": "assessment",
    }

  @staticmethod
  def _get_dropdown_payload():
    """Gets payload for dropdown CAD.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "title": "CAD Dropdown",
        "attribute_type": "Dropdown",
        "definition_type": "assessment",
        "multi_choice_options": "1,3,2",
    }

  @staticmethod
  def _get_multiselect_payload():
    """Gets payload for multiselect CAD.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "title": "CAD Multiselect",
        "attribute_type": "Multiselect",
        "definition_type": "assessment",
        "multi_choice_options": "1,3,2",
    }

  @staticmethod
  def _get_checkbox_payload():
    """Gets payload for checkbox CAD.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "title": "CAD Checkbox",
        "attribute_type": "Checkbox",
        "definition_type": "assessment",
    }

  @staticmethod
  def _get_map_person_payload():
    """Gets payload for checkbox CAD.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "title": "CAD Person",
        "attribute_type": "Map:Person",
        "definition_type": "assessment",
    }

  @classmethod
  def _get_payload(cls, attribute_type):
    """Gets payload for CAD by attribute type.

    Args:
      attribute_type: String representation of attribute type.
    Returns:
      Dictionary with attribute configuration.
    """
    payload_handlers = {
        "Text": cls._get_text_payload,
        "Rich Text": cls._get_rich_text_payload,
        "Date": cls._get_date_payload,
        "Dropdown": cls._get_dropdown_payload,
        "Multiselect": cls._get_multiselect_payload,
        "Checkbox": cls._get_checkbox_payload,
        "Map:Person": cls._get_map_person_payload,
    }

    return payload_handlers[attribute_type]()

  @staticmethod
  def _generate_assessment_response(*assessments):
    """Generate assessment test stub"""
    return [{
        "assessment_type": asmt.assessment_type,
        "id": asmt.id,
        "slug": asmt.slug,
        "title": asmt.title,
        "status": asmt.status,
        "urls_count": len(asmt.evidences_url),
        "files_count": len(asmt.evidences_file),
    } for asmt in assessments]

  def assert_request(self, expected_response):
    """Check if data in response is the same with expected."""
    response = self.client.post(
        self.ENDPOINT_URL,
        data=json.dumps(self.query),
        headers=self.headers
    )
    self.assert200(response)
    self.assertEqual(expected_response, response.json)

  @ddt.data(
      "Text",
      "Rich Text",
      "Date",
      "Dropdown",
      "Multiselect",
      "Checkbox",
      "Map:Person",
  )
  def test_simple_response(self, attribute_type):
    """Test search response {0} LCA for Assessment"""
    cad = factories.CustomAttributeDefinitionFactory(
        definition_id=self.asmt1.id,
        **self._get_payload(attribute_type)
    )
    expected_response = {
        "attributes": [{
            "title": cad.title,
            "mandatory": cad.mandatory,
            "attribute_type": cad.attribute_type,
            "default_value": cad.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad.id,
                    "multi_choice_options": cad.multi_choice_options,
                    "multi_choice_mandatory": cad.multi_choice_mandatory,
                }
            },
        }],
        "assessments": self._generate_assessment_response(self.asmt1),
    }
    self.assert_request(expected_response)

  def test_order_by(self):
    """Test search returns a proper sort of assessments data"""
    with factories.single_commit():
      self.asmt1.title = "B assessment"
      asmt2 = factories.AssessmentFactory(
          title="C assessment",
          assessment_type="Control",
          sox_302_enabled=True,
      )
      asmt3 = factories.AssessmentFactory(
          title="A assessment",
          assessment_type="Control",
          sox_302_enabled=True,
      )
      for asmt in [self.asmt1, asmt2, asmt3]:
        factories.CustomAttributeDefinitionFactory(
            definition_id=asmt.id,
            **self._get_payload("Text")
        )
    query = [{
        "object_name": "Assessment",
        "type": "ids",
        "filters": {"expression": {}},
        "order_by": [{"name": "title", "desc": True}]
    }]
    assessments = self._generate_assessment_response(asmt2, self.asmt1, asmt3)
    response = self.client.post(
        self.ENDPOINT_URL,
        data=json.dumps(query),
        headers=self.headers,
    )
    self.assert200(response)
    self.assertEqual(assessments, response.json["assessments"])

  def test_same_cads_one_with_value(self):
    """Test query 2 same cads and 1 with value mapped to 2 diff asmts"""
    with factories.single_commit():
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          **self._get_payload("Text")
      )
      factories.CustomAttributeValueFactory(
          custom_attribute=cad1,
          attributable=self.asmt1,
          attribute_value="test_value",
      )
      asmt2 = factories.AssessmentFactory(
          assessment_type="Control",
          sox_302_enabled=True,
      )
      cad2 = factories.CustomAttributeDefinitionFactory(
          definition_id=asmt2.id,
          **self._get_payload("Text")
      )
    expected_response = {
        "attributes": [{
            "title": cad1.title,
            "mandatory": cad1.mandatory,
            "attribute_type": cad1.attribute_type,
            "default_value": cad1.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": "test_value",
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad1.id,
                    "multi_choice_options": cad1.multi_choice_options,
                    "multi_choice_mandatory": cad1.multi_choice_mandatory,
                },
                str(asmt2.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": asmt2.id,
                    "attribute_definition_id": cad2.id,
                    "multi_choice_options": cad2.multi_choice_options,
                    "multi_choice_mandatory": cad2.multi_choice_mandatory,
                }
            },
        }],
        "assessments": self._generate_assessment_response(self.asmt1, asmt2),
    }
    self.assert_request(expected_response)

  @ddt.data(
      ("mandatory", False, True),
      ("title", "test title 1", "test title 2"),
  )
  @ddt.unpack
  def test_diff_cads_by_unique_fields(self, attribute, value1, value2):
    """Test query 2 diff cads with diff {0} value"""
    with factories.single_commit():
      cad_payload = self._get_payload("Text")
      cad_payload[attribute] = value1
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          **cad_payload
      )
      asmt2 = factories.AssessmentFactory(
          assessment_type="Control",
          sox_302_enabled=True,
      )
      cad_payload[attribute] = value2
      cad2 = factories.CustomAttributeDefinitionFactory(
          definition_id=asmt2.id,
          **cad_payload
      )
    expected_response = {
        "attributes": [{
            "title": cad1.title,
            "mandatory": cad1.mandatory,
            "attribute_type": cad1.attribute_type,
            "default_value": cad1.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad1.id,
                    "multi_choice_options": None,
                    "multi_choice_mandatory": None,
                },
            },
        }, {
            "title": cad2.title,
            "mandatory": cad2.mandatory,
            "attribute_type": cad2.attribute_type,
            "default_value": cad2.default_value,
            "values": {
                str(asmt2.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": asmt2.id,
                    "attribute_definition_id": cad2.id,
                    "multi_choice_options": None,
                    "multi_choice_mandatory": None,
                }
            },
        }],
        "assessments": self._generate_assessment_response(self.asmt1, asmt2),
    }
    self.assert_request(expected_response)

  def test_diff_cads_by_attribute_type(self):
    # pylint: disable=invalid-name
    """Test query 2 diff cads with diff attribute types"""
    common_payload = {
        "title": "Test Title",
        "mandatory": True
    }
    text_payload = self._get_payload("Text")
    text_payload.update(common_payload)
    checkbox_payload = self._get_payload("Checkbox")
    checkbox_payload.update(common_payload)
    with factories.single_commit():
      text_cad = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          **text_payload
      )
      asmt2 = factories.AssessmentFactory(
          assessment_type="Control",
          sox_302_enabled=True,
      )
      checkbox_cad = factories.CustomAttributeDefinitionFactory(
          definition_id=asmt2.id,
          **checkbox_payload
      )
    expected_response = {
        "attributes": [{
            "title": "Test Title",
            "mandatory": True,
            "attribute_type": "Text",
            "default_value": text_cad.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": text_cad.id,
                    "multi_choice_options": None,
                    "multi_choice_mandatory": None,
                },
            },
        }, {
            "title": "Test Title",
            "mandatory": True,
            "attribute_type": "Checkbox",
            "default_value": checkbox_cad.default_value,
            "values": {
                str(asmt2.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": asmt2.id,
                    "attribute_definition_id": checkbox_cad.id,
                    "multi_choice_options": None,
                    "multi_choice_mandatory": None,
                }
            },
        }],
        "assessments": self._generate_assessment_response(self.asmt1, asmt2),
    }
    self.assert_request(expected_response)

  def test_map_person_value(self):
    """Test Map:Person type value"""
    with factories.single_commit():
      person = factories.PersonFactory()
      cad = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          **self._get_payload("Map:Person")
      )
      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=self.asmt1,
          attribute_value=person.type,
          attribute_object_id=str(person.id),
      )
    expected_response = {
        "attributes": [{
            "title": cad.title,
            "mandatory": cad.mandatory,
            "attribute_type": cad.attribute_type,
            "default_value": cad.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": "Person",
                    "attribute_person_id": person.id,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad.id,
                    "multi_choice_options": cad.multi_choice_options,
                    "multi_choice_mandatory": cad.multi_choice_mandatory,
                },
            },
        }],
        "assessments": self._generate_assessment_response(self.asmt1),
    }
    self.assert_request(expected_response)

  def test_assessment_no_cads(self):
    """Test query assessment without local custom attributes"""
    expected_response = {
        "attributes": [],
        "assessments": self._generate_assessment_response(self.asmt1),
    }
    self.assert_request(expected_response)

  def test_two_assessments_one_no_cads(self):
    # pylint: disable=invalid-name
    """Test query two assessments where one has no any lca"""
    with factories.single_commit():
      cad = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          **self._get_payload("Text")
      )
      asmt2 = factories.AssessmentFactory(
          assessment_type="Control",
          sox_302_enabled=True,
      )
    expected_response = {
        "attributes": [{
            "title": cad.title,
            "mandatory": cad.mandatory,
            "attribute_type": cad.attribute_type,
            "default_value": cad.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad.id,
                    "multi_choice_options": cad.multi_choice_options,
                    "multi_choice_mandatory": cad.multi_choice_mandatory,
                }
            },
        }],
        "assessments": self._generate_assessment_response(self.asmt1, asmt2),
    }
    self.assert_request(expected_response)

  def test_one_assessments_many_cads(self):
    """Test one assessment with many cads"""
    with factories.single_commit():
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          **self._get_payload("Text")
      )
      cad2 = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          **self._get_payload("Dropdown")
      )
    expected_response = {
        "attributes": [{
            "title": cad1.title,
            "mandatory": cad1.mandatory,
            "attribute_type": cad1.attribute_type,
            "default_value": cad1.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad1.id,
                    "multi_choice_options": cad1.multi_choice_options,
                    "multi_choice_mandatory": cad1.multi_choice_mandatory,
                }
            },
        }, {
            "title": cad2.title,
            "mandatory": cad2.mandatory,
            "attribute_type": cad2.attribute_type,
            "default_value": cad2.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": None,
                    "attribute_person_id": None,
                    "preconditions_failed": None,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad2.id,
                    "multi_choice_options": cad2.multi_choice_options,
                    "multi_choice_mandatory": cad2.multi_choice_mandatory,
                }
            }
        }],
        "assessments": self._generate_assessment_response(self.asmt1),
    }
    self.assert_request(expected_response)

  @ddt.data(
      ("4,4", ['url']),
      ("2,2", ['evidence']),
      ("1,1", ['comment']),
  )
  @ddt.unpack
  def test_precondition_failed(
      self,
      multi_choice_mandatory,
      preconditions_failed,
  ):
    """Test search matrix with precondition failed cad"""
    with factories.single_commit():
      cad = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          multi_choice_mandatory=multi_choice_mandatory,
          **self._get_payload("Dropdown")
      )
      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=self.asmt1,
          attribute_value="1",
      )
    expected_response = {
        "attributes": [{
            "title": cad.title,
            "mandatory": cad.mandatory,
            "attribute_type": cad.attribute_type,
            "default_value": cad.default_value,
            "values": {
                str(self.asmt1.id): {
                    "value": "1",
                    "attribute_person_id": None,
                    "preconditions_failed": preconditions_failed,
                    "definition_id": self.asmt1.id,
                    "attribute_definition_id": cad.id,
                    "multi_choice_options": cad.multi_choice_options,
                    "multi_choice_mandatory": cad.multi_choice_mandatory,
                },
            },
        }],
        "assessments": self._generate_assessment_response(self.asmt1),
    }
    self.assert_request(expected_response)

  @ddt.data(all_models.Evidence.URL, all_models.Evidence.FILE)
  def test_asmt_has_evidences(self, kind):
    """Test search matrix assessments with evidences"""
    with factories.single_commit():
      cad = factories.CustomAttributeDefinitionFactory(
          definition_id=self.asmt1.id,
          multi_choice_mandatory="4,4",
          **self._get_payload("Dropdown")
      )
      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=self.asmt1,
          attribute_value="1",
      )
    asmt_id = self.asmt1.id
    new_evidence = factories.EvidenceFactory(kind=kind)
    response = self.api.put(self.asmt1, {
        "actions": {"add_related": [
            {"id": new_evidence.id, "type": "Evidence"},
        ]},
    })
    self.assertEqual(response.status_code, 200)
    assessments = self._generate_assessment_response(
        all_models.Assessment.query.get(asmt_id),
    )
    response = self.client.post(
        self.ENDPOINT_URL,
        headers=self.headers,
        data=json.dumps(self.query),
    )
    self.assert200(response)
    self.assertEqual(assessments, response.json["assessments"])