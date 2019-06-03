/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canMap from 'can-map';
import canComponent from 'can-component';
import * as StateUtils from '../../plugins/utils/state-utils';
import {getAvailableAttributes} from '../../plugins/utils/tree-view-utils';
import * as AdvancedSearch from '../../plugins/utils/advanced-search-utils';

export default canComponent.extend({
  tag: 'advanced-search-wrapper',
  leakScope: true,
  viewModel: canMap.extend({
    define: {
      hasStatusFilter: {
        get: function () {
          return StateUtils.hasFilter(this.attr('modelName'));
        },
      },
      filtersToApply: {
        set(filters) {
          if (filters) {
            const {
              filterItems = [],
              mappingItems = [],
              statusItem,
            } = filters;

            this.attr('filterItems', filterItems);
            this.attr('mappingItems', mappingItems);
            this.attr('statusItem', statusItem);

            this.dispatch('applyFilters');
          }
        },
      },
    },
    modelName: null,
    modelDisplayName: null,
    filterItems: [AdvancedSearch.create.attribute()],
    mappingItems: [],
    statusItem: AdvancedSearch.create.state(),
    relevantTo: [],
    availableAttributes: function () {
      return getAvailableAttributes(this.attr('modelName'));
    },
    addFilterAttribute: function () {
      let items = this.attr('filterItems');
      if (items.length) {
        items.push(AdvancedSearch.create.operator('AND'));
      }
      items.push(AdvancedSearch.create.attribute());
    },
    addMappingFilter: function () {
      let items = this.attr('mappingItems');
      if (items.length) {
        items.push(AdvancedSearch.create.operator('AND'));
      }
      items.push(AdvancedSearch.create.mappingCriteria());
    },
    resetFilters: function () {
      this.attr('filterItems', [AdvancedSearch.create.attribute()]);
      this.attr('mappingItems', []);
      this.setDefaultStatusItem();
    },
    setDefaultStatusItem: function () {
      if (this.attr('hasStatusFilter')) {
        const defaultStatusItem = AdvancedSearch.setDefaultStatusConfig(
          this.attr('statusItem.value'), this.attr('modelName')
        );
        this.attr('statusItem.value', defaultStatusItem);
      } else {
        this.attr('statusItem', AdvancedSearch.create.state());
      }
    },
  }),
  events: {
    '{viewModel} modelName': function () {
      this.viewModel.resetFilters();
    },
  },
  init: function () {
    this.viewModel.setDefaultStatusItem();
  },
});
