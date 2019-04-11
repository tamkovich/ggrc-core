# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for Risk model."""

import datetime

from ggrc.models import all_models
from integration.ggrc import TestCase
from integration.ggrc import api_helper
from integration.ggrc.models import factories


class TestRiskGGRC(TestCase):
  """Tests for risk model for GGRC users."""

  def setUp(self):
    """setUp, nothing else to add."""
    super(TestRiskGGRC, self).setUp()
    self.api = api_helper.Api()

  def test_create(self):
    """Test risk create with internal user."""
    response = self.api.post(all_models.Risk, {"title": "new-title"})
    self.assert403(response)

    risk_count = all_models.Risk.query.filter(
        all_models.Risk.title == "new-title").count()
    self.assertEqual(0, risk_count)

  def test_update(self):
    """Test risk update with internal user."""
    risk = factories.RiskFactory()
    old_title = risk.title

    response = self.api.put(risk, {"title": "new-title"})
    self.assert403(response)

    risk = all_models.Risk.query.get(risk.id)
    self.assertEqual(old_title, risk.title)

  def test_delete(self):
    """Test risk delete with internal user."""
    risk = factories.RiskFactory()

    response = self.api.delete(risk)
    self.assert403(response)

    risk = all_models.Risk.query.get(risk.id)
    self.assertIsNotNone(risk.title)


class TestRiskGGRCQ(TestCase):
  """Tests for risk model for GGRCQ users."""

  def setUp(self):
    """setUp, nothing else to add."""
    super(TestRiskGGRCQ, self).setUp()
    self.api = api_helper.Api()
    self.api.login_as_external()

  @staticmethod
  def generate_risk_body():
    """Generate JSON body for Risk."""
    body = {
        "id": 10,
        "title": "External risk",
        "risk_type": "External risk",
        "created_at": datetime.datetime(2019, 1, 1, 12, 30),
        "updated_at": datetime.datetime(2019, 1, 2, 13, 30),
        "external_id": 10,
        "external_slug": "external_slug"
    }

    return body

  def assert_instance(self, expected, risk):
    """Compare expected response body with actual."""
    risk_values = {}
    expected_values = {}

    for field, value in expected.items():
      expected_values[field] = value
      risk_values[field] = getattr(risk, field, None)

    self.assertEqual(expected_values, risk_values)

  def test_create(self):
    """Test risk create with external user."""
    risk_body = self.generate_risk_body()

    response = self.api.post(all_models.Risk, {
        "risk": risk_body
    })

    self.assertEqual(201, response.status_code)

    risk = all_models.Risk.query.get(risk_body["id"])
    self.assert_instance(risk_body, risk)

  def test_update(self):
    """Test risk update with external user."""
    with factories.single_commit():
      risk_id = factories.RiskFactory().id

    new_values = {
        "title": "New risk",
        "created_at": datetime.datetime(2019, 1, 3, 14, 30),
        "updated_at": datetime.datetime(2019, 1, 4, 14, 30)
    }

    risk = all_models.Risk.query.get(risk_id)
    response = self.api.put(risk, new_values)

    self.assertEqual(200, response.status_code)

    risk = all_models.Risk.query.get(risk_id)
    self.assert_instance(new_values, risk)
