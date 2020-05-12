# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module containing comment model and comment related mixins."""

import itertools

from collections import defaultdict

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import validates

from ggrc import builder
from ggrc import db
from ggrc.models import custom_attribute_definition
from ggrc.models.deferred import deferred
from ggrc.models.mixins import base, synchronizable
from ggrc.models.mixins import Base
from ggrc.models.mixins import Described
from ggrc.models.mixins import Notifiable
from ggrc.models.relationship import Relatable, Relationship
from ggrc.access_control.roleable import Roleable
from ggrc.fulltext.mixin import Indexed, ReindexRule
from ggrc.fulltext.attributes import MultipleSubpropertyFullTextAttr
from ggrc.models import inflector
from ggrc.models import reflection
from ggrc.models import utils


class Commentable(object):
  """Mixin for commentable objects.

  This is a mixin for adding default options to objects on which people can
  comment.

  recipients is used for setting who gets notified (Verifer, Requester, ...).
  send_by_default should be used for setting the "send notification" flag in
  the comment modal.

  """
  # pylint: disable=too-few-public-methods

  VALID_RECIPIENTS = frozenset([
      "Assignees",
      "Creators",
      "Verifiers",
      "Admin",
      "Primary Contacts",
      "Secondary Contacts",
  ])

  @validates("recipients")
  def validate_recipients(self, key, value):
    """
      Validate recipients list

      Args:
        value (string): Can be either empty, or
                        list of comma separated `VALID_RECIPIENTS`
    """
    # pylint: disable=unused-argument
    if value:
      value = set(name for name in value.split(",") if name)

    if value and value.issubset(self.VALID_RECIPIENTS):
      # The validator is a bit more smart and also makes some filtering of the
      # given data - this is intended.
      return ",".join(value)
    elif not value:
      return ""
    else:
      raise ValueError(value,
                       'Value should be either empty ' +
                       'or comma separated list of ' +
                       ', '.join(sorted(self.VALID_RECIPIENTS))
                       )

  recipients = db.Column(
      db.String,
      nullable=True,
      default=u"Assignees,Creators,Verifiers")

  send_by_default = db.Column(db.Boolean, nullable=False, default=True)

  _api_attrs = reflection.ApiAttributes("recipients", "send_by_default")

  _aliases = {
      "recipients": {
          "display_name": "Recipients",
          "description": "Automatically provided values"
      },
      "send_by_default": {
          "display_name": "Send by default",
          "description": "Automatically provided values",
      },
      "comments": {
          "display_name": "Comments",
          "description": (
              u'Multiple values are allowed.'
              u' Delimiter is "double semi-colon separated values" (";;")".'
              u' To mention person at the comment use the following format '
              u'<a href="mailto:some_user@example.com">'
              u'+some_user@example.com</a>.'
          ),
      },
  }
  _fulltext_attrs = [
      MultipleSubpropertyFullTextAttr("comment", "comments", ["description"]),
  ]

  @classmethod
  def indexed_query(cls):
    return super(Commentable, cls).indexed_query().options(
        orm.Load(cls).subqueryload("comments").load_only("id", "description")
    )

  @classmethod
  def eager_query(cls, **kwargs):
    """Eager Query"""
    query = super(Commentable, cls).eager_query(**kwargs)
    return query.options(orm.subqueryload('comments'))

  @declared_attr
  def comments(cls):  # pylint: disable=no-self-argument
    """Comments related to self via Relationship table."""
    return db.relationship(
        Comment,
        primaryjoin=lambda: sa.or_(
            sa.and_(
                cls.id == Relationship.source_id,
                Relationship.source_type == cls.__name__,
                Relationship.destination_type == "Comment",
            ),
            sa.and_(
                cls.id == Relationship.destination_id,
                Relationship.destination_type == cls.__name__,
                Relationship.source_type == "Comment",
            )
        ),
        secondary=Relationship.__table__,
        secondaryjoin=lambda: sa.or_(
            sa.and_(
                Comment.id == Relationship.source_id,
                Relationship.source_type == "Comment",
            ),
            sa.and_(
                Comment.id == Relationship.destination_id,
                Relationship.destination_type == "Comment",
            )
        ),
        viewonly=True,
    )


def reindex_by_relationship(relationship):
  """Reindex comment if relationship changed or created or deleted"""
  if relationship.destination_type == Comment.__name__:
    instance = relationship.source
  elif relationship.source_type == Comment.__name__:
    instance = relationship.destination
  else:
    return []
  if isinstance(instance, (Indexed, Commentable)):
    return [instance]
  return []


def get_objects_to_reindex(obj):
  """Return list of Commentable objects related to provided comment."""
  source_qs = db.session.query(
      Relationship.destination_type, Relationship.destination_id
  ).filter(
      Relationship.source_type == obj.type,
      Relationship.source_id == obj.id
  )
  destination_qs = db.session.query(
      Relationship.source_type, Relationship.source_id
  ).filter(
      Relationship.destination_type == obj.type,
      Relationship.destination_id == obj.id
  )
  result_qs = source_qs.union(destination_qs)
  klass_dict = defaultdict(set)
  for klass, object_id in result_qs:
    klass_dict[klass].add(object_id)

  queries = []
  for klass, object_ids in klass_dict.iteritems():
    model = inflector.get_model(klass)
    if not model:
      continue
    if issubclass(model, (Indexed, Commentable, ExternalCommentable)):
      queries.append(model.query.filter(model.id.in_(list(object_ids))))
  return list(itertools.chain(*queries))


class Comment(
    custom_attribute_definition.CustomAttributeDefinitionFK,
    Roleable,
    Relatable,
    Described,
    Notifiable,
    base.ContextRBAC,
    Base,
    Indexed,
    db.Model,
):
  """Basic comment model."""
  __tablename__ = "comments"

  assignee_type = db.Column(db.String, nullable=False, default=u"")

  initiator_instance_id = db.Column(db.Integer, nullable=True)
  initiator_instance_type = db.Column(db.String, nullable=True)
  INITIATOR_INSTANCE_TMPL = "{}_comment_initiated_by"

  initiator_instance = utils.PolymorphicRelationship("initiator_instance_id",
                                                     "initiator_instance_type",
                                                     INITIATOR_INSTANCE_TMPL)

  # REST properties
  _api_attrs = reflection.ApiAttributes(
      "assignee_type",
      reflection.Attribute(
          "header_url_link",
          create=False,
          update=False,
      ),
  )

  _sanitize_html = [
      "description",
  ]

  AUTO_REINDEX_RULES = [
      ReindexRule("Comment", get_objects_to_reindex),
      ReindexRule("Relationship", reindex_by_relationship),
  ]

  @builder.simple_property
  def header_url_link(self):
    """Return header url link to comment if that comment related to proposal
    and that proposal is only proposed."""
    if self.initiator_instance_type != "Proposal":
      return ""
    proposed_status = self.initiator_instance.STATES.PROPOSED
    if self.initiator_instance.status == proposed_status:
      return "proposal_link"
    return ""


class ExternalComment(
    synchronizable.Synchronizable,
    synchronizable.RoleableSynchronizable,
    Relatable,
    Described,
    base.ContextRBAC,
    Base,
    Indexed,
    db.Model
):
  """External comment model."""
  __tablename__ = "external_comments"

  assignee_type = db.Column(db.String, nullable=False, default=u"")

  _api_attrs = reflection.ApiAttributes(
      "assignee_type",
  )

  _sanitize_html = [
      "description",
  ]

  AUTO_REINDEX_RULES = [
      ReindexRule("ExternalComment", get_objects_to_reindex),
      ReindexRule("Relationship", reindex_by_relationship),
  ]


class ExternalCommentable(object):
  """Mixin for external commentable objects.

  This is a mixin for adding external comments (comments that can be
  created only by sync service) to the object.
  """
  _fulltext_attrs = [
      MultipleSubpropertyFullTextAttr("comment", "comments", ["description"]),
  ]

  @classmethod
  def indexed_query(cls):
    """Indexed query for ExternalCommentable mixin."""
    return super(ExternalCommentable, cls).indexed_query().options(
        orm.Load(cls).subqueryload("comments").load_only("id", "description")
    )

  @classmethod
  def eager_query(cls, **kwargs):
    """Eager query for ExternalCommentable mixin."""
    query = super(ExternalCommentable, cls).eager_query(**kwargs)
    return query.options(orm.subqueryload("comments"))

  @declared_attr
  def comments(cls):  # pylint: disable=no-self-argument
    """ExternalComment related to self via Relationship table."""
    return db.relationship(
        ExternalComment,
        primaryjoin=lambda: sa.or_(
            sa.and_(
                cls.id == Relationship.source_id,
                Relationship.source_type == cls.__name__,
                Relationship.destination_type == ExternalComment.__name__,
            ),
            sa.and_(
                cls.id == Relationship.destination_id,
                Relationship.destination_type == cls.__name__,
                Relationship.source_type == ExternalComment.__name__,
            )
        ),
        secondary=Relationship.__table__,
        secondaryjoin=lambda: sa.or_(
            sa.and_(
                ExternalComment.id == Relationship.source_id,
                Relationship.source_type == ExternalComment.__name__,
            ),
            sa.and_(
                ExternalComment.id == Relationship.destination_id,
                Relationship.destination_type == ExternalComment.__name__,
            )
        ),
        viewonly=True,
    )


class CommentInitiator(object):  # pylint: disable=too-few-public-methods
  """Mixin for comment initiating"""
  @sa.ext.declarative.declared_attr
  def initiator_comments(cls):  # pylint: disable=no-self-argument
    """Relationship.

    Links comments to object that are the reason of that comment generation."""

    def join_function():
      return sa.and_(
          sa.orm.foreign(Comment.initiator_instance_type) == cls.__name__,
          sa.orm.foreign(Comment.initiator_instance_id) == cls.id,
      )

    return sa.orm.relationship(
        Comment,
        primaryjoin=join_function,
        backref=Comment.INITIATOR_INSTANCE_TMPL.format(cls.__name__),
    )


class ScopedCommentable(ExternalCommentable):
  """Mixin for external commentable scoping objects."""
  pass
