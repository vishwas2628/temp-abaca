django.jQuery(function ($) {
  'use strict';

  // Filter company_list options based on selected Company
  $('#id_company').on('change', function () {
    const companyId = this.value;
    $.get(`/companies/${companyId}/company-lists`, data => { 
      $('.field-company_list select').each(function () {
        const selectedCompanyListId = this.value;
        $(this).find('option:not(:first-child)').remove()
        $(this).append(data.map(({id, title}) => `<option value="${id}">${title}</option>`));
        $(this).find(`option[value="${selectedCompanyListId}"]`).prop('selected', true);
      });
    });
  }).trigger('change');

  // Add help text under each Step's company_list field
  $('.field-company_list > .related-widget-wrapper').append(
    `<div><small>${
      $('.column-company_list > .help').attr('title')
    }</small></div>`
  );  

});