/*
  Copyright (C) 2020 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import canComponent from 'can-component';
import canDefineMap from 'can-define/map/map';
import canStache from 'can-stache';
import template from './assessments-bulk-complete-table.stache';
import './assessments-bulk-complete-table-header/assessments-bulk-complete-table-header';
import './assessments-bulk-complete-table-row/assessments-bulk-complete-table-row';
import {getCustomAttributeType} from '../../../plugins/utils/ca-utils';

const ViewModel = canDefineMap.extend({seal: false}, {
  assessmentsList: {
    value: () => [],
  },
  attributesList: {
    value: () => [],
  },
  headersData: {
    value: () => [],
  },
  rowsData: {
    value: () => [],
  },
  buildHeadersData() {
    return this.attributesList.map((attribute) => ({
      title: attribute.title,
      mandatory: attribute.mandatory,
    }));
  },
  buildRowsData() {
    const rowsData = [];

    this.assessmentsList.forEach((assessment) => {
      const assessmentData = {
        asmtId: assessment.id,
        asmtTitle: assessment.title,
        asmtStatus: assessment.status,
        asmtType: assessment.assessment_type,
        urlsCount: assessment.urls_count,
        filesCount: assessment.files_count,
      };
      const attributesData = [];

      this.attributesList.forEach((attribute) => {
        let id = null;
        let value = null;
        let optionsList = [];
        let optionsConfig = new Map();
        let isApplicable = false;
        let errorsMap = {
          file: false,
          url: false,
          comment: false,
        };
        const type = getCustomAttributeType(attribute.attribute_type);
        const defaultValue = this.prepareAttributeValue(type,
          attribute.default_value);

        const assessmentAttributeData = attribute.values[assessment.id];
        if (assessmentAttributeData) {
          id = assessmentAttributeData.attribute_definition_id;
          value = this.prepareAttributeValue(type,
            assessmentAttributeData.value,
            assessmentAttributeData.attribute_person_id);
          ({optionsList, optionsConfig} = this.prepareMultiChoiceOptions(
            assessmentAttributeData.multi_choice_options,
            assessmentAttributeData.multi_choice_mandatory)
          );
          isApplicable = true;

          if (assessmentAttributeData.preconditions_failed) {
            const errors =
              assessmentAttributeData.preconditions_failed.serialize();
            errorsMap = {
              file: errors.includes('evidence'),
              url: errors.includes('url'),
              comment: errors.includes('comment'),
            };
          }
        }

        attributesData.push({
          id,
          type,
          value,
          defaultValue,
          isApplicable,
          errorsMap,
          title: attribute.title,
          mandatory: attribute.mandatory,
          multiChoiceOptions: {
            values: optionsList,
            config: optionsConfig,
          },
          attachments: null,
          modified: false,
          validation: {
            mandatory: attribute.mandatory,
            valid: (isApplicable ? !attribute.mandatory : true),
            requiresAttachment: false,
            hasMissingInfo: false,
          },
        });
      });

      rowsData.push({attributes: attributesData, ...assessmentData});
    });

    return rowsData;
  },
  prepareAttributeValue(type, value, personId = null) {
    switch (type) {
      case 'checkbox':
        return value === '1';
      case 'date':
        return value || null;
      case 'dropdown':
        return value || '';
      case 'multiselect':
        return value || '';
      case 'person':
        return personId
          ? [{
            id: personId,
            type: 'Person',
            href: `/api/people/${personId}`,
            context_id: null,
          }]
          : null;
      default:
        return value;
    }
  },
  prepareMultiChoiceOptions(multiChoiceOptions, multiChoiceMandatory) {
    const optionsList = this.convertToArray(multiChoiceOptions);
    const optionsStates = this.convertToArray(multiChoiceMandatory);
    const optionsConfig = optionsStates.reduce((config, state, index) => {
      const optionValue = optionsList[index];
      return config.set(optionValue, Number(state));
    }, new Map());

    return {optionsList, optionsConfig};
  },
  convertToArray(value) {
    return typeof value === 'string' ? value.split(',') : [];
  },
  init() {
    this.headersData = this.buildHeadersData();
    this.rowsData = this.buildRowsData();
  },
});

export default canComponent.extend({
  tag: 'assessments-bulk-complete-table',
  view: canStache(template),
  ViewModel,
});