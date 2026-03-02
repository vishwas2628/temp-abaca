django.jQuery(function ($) {
    'use strict';

    var teamMemberQuestionIDs = JSON.parse($('#team_member_question_ids').val() || "[]")
    var $questionsListItems = $('#id_questions + ul.sortedm2m-items > li.sortedm2m-item');
    var $teamMemberQuestionsCheckbox = $('#id_has_team_member_questions');
    var $filterInput = $('#id_questions').siblings('.selector-filter').find('input');

    function syncQuestionsVisiblity() {
        var bundleHasTeamMemberQuestions = $teamMemberQuestionsCheckbox.prop('checked');
        $questionsListItems.each(function (index, item) {
            var questionID = parseInt( $(this).find('input').val() )
            var isTeamMemberQuestion = teamMemberQuestionIDs.includes(questionID)

            if (isTeamMemberQuestion == bundleHasTeamMemberQuestions) {
                $(item).removeClass('hidden');
            } else {
                $(item).addClass('hidden');
                $(item).find('input[type="checkbox"]').prop('checked', false);
            }
        });
    }

    $teamMemberQuestionsCheckbox.on('change', syncQuestionsVisiblity).trigger('change');
    $filterInput.on('input', syncQuestionsVisiblity);
});