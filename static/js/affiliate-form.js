django.jQuery(function ($) {
	"use strict";

	var isUpdatingJobStatus = false;
	var isDownloadingReport = false;
	var isGeneratingSDGReports = false;
	var isRegeneratingSpreadsheet = false;

	$("#regenerate-spreadsheet").on("click", function () {
		if (isRegeneratingSpreadsheet) return false;

		var $button = $(this);

		if (confirm("Are you sure? This actions is irreversible.")) {
			isRegeneratingSpreadsheet = true;
			$button.addClass("loading");

			$.ajax($button.attr("href"), {
				type: "POST",
				success: function () {
					alert("The spreadsheet was regenerated successfully! This page will now reload.");
					window.location.reload();
				},
				error: function (response) {
					alert(`The Google API returned the following error: ${response.statusText}. Please try again later.`);
				},
				complete: function () {
					isRegeneratingSpreadsheet = false;
					$button.removeClass("loading");
				},
			});
		}

		$button.blur();

		return false;
	});

	$("#generate-sdg-reports").on("click", function () {
		console.log("generate-sdg-reports");
		if (isGeneratingSDGReports) return false;

		var $button = $(this);
		$button.addClass("loading");

		$.ajax($button.attr("href"), {
			type: "POST",
			success: function () {
				alert("The report generation was successfully started. You can download the report once it's ready.");
				window.location.reload();
			},
			error: function (response) {
				alert(`The failed to generate the report: ${response.statusText}. Please try again later.`);
			},
			complete: function () {
				isGeneratingSDGReports = false;
				$button.removeClass("loading");
			},
		});

		$button.blur();
		return false;
	});

	$("#update_job_status").on("click", function () {
		if (isUpdatingJobStatus) return false;

		var $button = $(this);
		$button.addClass("loading");
		console.log($button.attr("href"));

		$.ajax($button.attr("href"), {
			type: "POST",
			success: function () {
				alert("The job status was successfully updated.");
				window.location.reload();
			},
			error: function (response) {
				alert(`The failed to update the job status: ${response.statusText}. Please try again later.`);
			},
			complete: function () {
				isUpdatingJobStatus = false;
				$button.removeClass("loading");
			},
		});

		$button.blur();
		return false;
	});

	$("#id_show_team_section")
		.on("change", function () {
			$(".field-team_question_bundles").toggle($(this).prop("checked"));
		})
		.trigger("change");

	// Handle flow type change event
	$("#id_flow_type").on("change", function (event) {
		toggleAffiliateCustomizationTab();
	});

	// Handle flow target change event
	$("#id_flow_target").on("change", function (event) {
		toggleAffiliateCustomizationTab();
	});

	// Handle tab click event
	$(".nav-link").click(function (event) {
		event.preventDefault();

		// Remove active class from all tabs
		$(".nav-link").removeClass("active");

		// Add active class to the clicked tab
		$(this).addClass("active");

		// Call toggleFieldsets to update fieldsets
		toggleFieldsets();
	});

	// Function to show/hide fieldsets based on active tab
	function toggleFieldsets() {
		const tab1 = $("#affiliate-configuration");
		const translationSelect = $("#modeltranslation-main-switch");
		const tools = $(".object-tools");
		const configurationContent = $(".configuration");
		const leftPanelContent = $(".left-panel");
		const selfAssessmentContent = $(".self-assessment-step");
		const questionsContent = $(".questions-step");
		const teamMembersContent = $(".team-members-step");
		const fieldsetTitle = $("fieldset h2");
		const landingPageImg = $(".landing-page-example");

		if (tab1.hasClass("active")) {
			$(configurationContent).show();
			$(leftPanelContent).hide();
			$(selfAssessmentContent).hide();
			$(questionsContent).hide();
			$(teamMembersContent).hide();
			$(translationSelect).hide();
			$(tools).show();
			$(fieldsetTitle).hide();
			$(landingPageImg).hide();
		} else {
			$(configurationContent).hide();
			$(leftPanelContent).show();
			$(selfAssessmentContent).show();
			$(questionsContent).show();
			$(teamMembersContent).show();
			$(translationSelect).show();
			$(tools).hide();
			$(fieldsetTitle).show();
			$(landingPageImg).show();
		}
	}

	// Function to show/hide affiliate customization fieldset based on flow type
	function toggleAffiliateCustomizationTab() {
		const flowType = $("#id_flow_type").val();
		const flowTarget = $("#id_flow_target").val();
		const isAffiliateQuestionBundleType = flowType == 1;
		const isAffiliateForEntrepreneurs = flowTarget == 0;

		if (isAffiliateQuestionBundleType && isAffiliateForEntrepreneurs) {
			$(".affiliate-customization").show();
		} else {
			$(".affiliate-customization").hide();
		}
	}

	$(document).ready(function () {
		toggleFieldsets();
		toggleAffiliateCustomizationTab();
	});
});
