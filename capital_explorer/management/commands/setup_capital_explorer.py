import datetime
from django.core.management import BaseCommand

from matching.models import Answer, Question, QuestionCategory
from capital_explorer.models import CompanyStage, FundingCriteria, FundingSource, FundingStage, FundingType


class Command(BaseCommand):
    help = 'Script to set up the Capital Explorer app'

    def handle(self, *args, **options):
        FundingCriteria.objects.all().delete()
        FundingType.objects.all().delete()
        FundingStage.objects.all().delete()
        CompanyStage.objects.all().delete()
        FundingSource.objects.all().delete()

        FundingType.objects.bulk_create(
            [
                dilutive := FundingType(id=1, name='Dilutive'),
                non_dilutive := FundingType(id=2, name='Non-dilutive'),
            ]
        )

        FundingStage.objects.bulk_create(
            [
                pre_revenue := FundingStage(id=1, name='Pre-revenue'),
                revenue_generating := FundingStage(id=2, name='Revenue generating'),
            ]
        )

        CompanyStage.objects.bulk_create(
            [
                concept := CompanyStage(name='Concept'),
                early := CompanyStage(name='Early'),
                growth := CompanyStage(name='Growth'),
                scaling := CompanyStage(name='Scaling'),
                established := CompanyStage(name='Established'),
            ]
        )

        FundingSource.objects.bulk_create([
            convertible_grants := FundingSource(name="Convertible Grants", description="Grant that converts into equity"),
            debt_crowdfunding := FundingSource(name="Debt Crowdfunding", description="Loan that is funded by a group of individuals (commonly known as peer-to-peer lending)"),
            equity_crowdfunding := FundingSource(name="Equity Crowdfunding", description="Sale of ownership in a company to a group of individuals"),
            equity := FundingSource(name="Equity", description="Sale of ownership or the future right to ownership in a company (priced equity, SAFE, convertible debt)"),
            forgivable_loans := FundingSource(name="Forgivable Loans", description="Debt that converts into a grant"),
            prizes := FundingSource(name="Prizes", description="Awards typically derived from pitch competitions or other luck or merit-based contests from organizations that support early-stage entrepreneurs.\n\nAwards can be cash, services, or other financing vehicles."),
            recoverable_grants := FundingSource(name="Recoverable Grants", description="Grant that converts into debt"),
            redeemable_equity := FundingSource(name="Redeemable Equity", description="Purchase of shares that can be bought back at a pre-agreed multiple or mutually agreed price."),
            revenue_based_loans := FundingSource(name="Revenue-Based Loans", description="Loan that is repaid as a percentage of future revenue or cash flows"),
            revenues := FundingSource(name="Revenues", description="Cash paid by customers for products or services rendered."),
            rewards_crowdfunding := FundingSource(name="Rewards Crowdfunding", description="Donation from a group of individuals towards a project or business with the expectation of receiving a non-financial reward in return, such as goods or services, at a later time."),
            secured_debt := FundingSource(name="Secured Debt", description="Loan that is secured by collateral."),
            sme_mezzanine_debt := FundingSource(name="SME Mezzanine Debt", description="A loan that is paid back with a fixed interest and has upside through kickers such as warrants or profit share"),
            supply_chain_financing := FundingSource(name="Supply Chain Financing", description="Short-term funding option that allows you to access working capital using your invoices, purchase orders or shipping bills"),
            traditional_grant := FundingSource(name="Traditional Grant", description="Capital that has no expectation of financial repayment"),
            venture_debt := FundingSource(name="Venture Debt", description="A variety of different types of loans made to fast growing venture backed companies"),
        ])

        convertible_grants.funding_types.set([dilutive])
        convertible_grants.funding_stages.set([pre_revenue, revenue_generating])
        convertible_grants.company_stages.set([concept, early, growth, scaling, established])

        debt_crowdfunding.funding_types.set([non_dilutive])
        debt_crowdfunding.funding_stages.set([revenue_generating])
        debt_crowdfunding.company_stages.set([early, growth, scaling, established])

        equity.funding_types.set([dilutive])
        equity.funding_stages.set([pre_revenue, revenue_generating])
        equity.company_stages.set([concept, early, growth])

        equity_crowdfunding.funding_types.set([dilutive])
        equity_crowdfunding.funding_stages.set([pre_revenue, revenue_generating])
        equity_crowdfunding.company_stages.set([early, growth, scaling, established])

        forgivable_loans.funding_types.set([non_dilutive])
        forgivable_loans.funding_stages.set([pre_revenue, revenue_generating])
        forgivable_loans.company_stages.set([concept, early, growth, scaling, established])

        sme_mezzanine_debt.funding_types.set([dilutive, non_dilutive])
        sme_mezzanine_debt.funding_stages.set([revenue_generating])
        sme_mezzanine_debt.company_stages.set([early, growth, scaling])

        prizes.funding_types.set([non_dilutive])
        prizes.funding_stages.set([pre_revenue, revenue_generating])
        prizes.company_stages.set([concept, early])

        recoverable_grants.funding_types.set([non_dilutive])
        recoverable_grants.funding_stages.set([pre_revenue, revenue_generating])
        recoverable_grants.company_stages.set([concept, early, growth, scaling, established])

        redeemable_equity.funding_types.set([dilutive])
        redeemable_equity.funding_stages.set([pre_revenue, revenue_generating])
        redeemable_equity.company_stages.set([concept, early, growth, scaling])

        revenue_based_loans.funding_types.set([non_dilutive])
        revenue_based_loans.funding_stages.set([revenue_generating])
        revenue_based_loans.company_stages.set([early, growth, scaling, established])

        revenues.funding_types.set([non_dilutive])
        revenues.funding_stages.set([revenue_generating])
        revenues.company_stages.set([early, growth, scaling, established])

        rewards_crowdfunding.funding_types.set([non_dilutive])
        rewards_crowdfunding.funding_stages.set([pre_revenue, revenue_generating])
        rewards_crowdfunding.company_stages.set([concept, early, growth, scaling, established])

        secured_debt.funding_types.set([non_dilutive])
        secured_debt.funding_stages.set([revenue_generating])
        secured_debt.company_stages.set([growth, scaling, established])

        supply_chain_financing.funding_types.set([non_dilutive])
        supply_chain_financing.funding_stages.set([revenue_generating])
        supply_chain_financing.company_stages.set([early, growth, scaling, established])

        traditional_grant.funding_types.set([non_dilutive])
        traditional_grant.funding_stages.set([pre_revenue, revenue_generating])
        traditional_grant.company_stages.set([concept, early, growth, scaling, established])

        venture_debt.funding_types.set([non_dilutive])
        venture_debt.funding_stages.set([revenue_generating])
        venture_debt.company_stages.set([early, growth, scaling])

        about_sample = '''<h4>🚀 Stage</h4>
<p>Most likely suitable for early, growth and scaling companies. While available for established companies, a fixed-term bank loan may be less expensive if they have the collateral or personal guarantees required.</p>
<h4>💰 Revenue (historical and recurrence)</h4>
<p>Lenders typically look for recurring or repeatable revenue.</p>
<h4>📊 Gross profit margins</h4>
<p>30%+ is desirable to ensure enough capital is available after monthly repayments to continue driving the company's growth.</p>
<h4>📈 Growth projections</h4>
<p>Loans are typically available to companies of all growth profiles.</p>
<h4>💼 Use of capital</h4>
<p>Working and growth capital.</p>
<h4>💡 Impact embeddedness and impact track record</h4>
<p>This is not a key determinant unless a lender only works with impact-driven companies.</p>'''
        FundingSource.objects.all().update(about=about_sample, key_characteristics=about_sample, key_implications=about_sample)

        capital_category = QuestionCategory.objects.update_or_create(
            name="Capital Structures",
            defaults={
                "name_en": "Capital Structures",
                "description": "Questions for the Capital Explorer",
                "description_en": "Questions for the Capital Explorer",
            }
        )[0]

        Question.objects.update_or_create(
            slug="CD_Geography",
            defaults={
                "entrepreneur_question": "Where is your startup headquartered?",
                "entrepreneur_question_en": "Where is your startup headquartered?",
                "resource_question": "Where would you like startups to be headquartered?",
                "resource_question_en": "Where would you like startups to be headquartered?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Geography",
                "short_name_en": "CD_Geography",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Funder_Involvement",
            defaults={
                "entrepreneur_question": "How involved would you like the capital provider to be in your business?",
                "entrepreneur_question_en": "How involved would you like the capital provider to be in your business?",
                "resource_question": "How involved would you be in the management of the business?",
                "resource_question_en": "How involved would you be in the management of the business?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Funder_Involvement",
                "short_name_en": "CD_Funder_Involvement",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Dilution",
            defaults={
                "entrepreneur_question": "Are you interested in dilutive or (and) non-dilutive capital options?",
                "entrepreneur_question_en": "Are you interested in dilutive or (and) non-dilutive capital options?",
                "resource_question": "Is the capital dilutive or non-dilutive?",
                "resource_question_en": "Is the capital dilutive or non-dilutive?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Dilution",
                "short_name_en": "CD_Dilution",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Repayment_Timeline",
            defaults={
                "entrepreneur_question": "How soon would you like to repay the capital?",
                "entrepreneur_question_en": "How soon would you like to repay the capital?",
                "resource_question": "How soon does the capital need to be repaid?",
                "resource_question_en": "How soon does the capital need to be repaid?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Repayment_Timeline",
                "short_name_en": "CD_Repayment_Timeline",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Repayment",
            defaults={
                "entrepreneur_question": "How would you like this capital to be repaid?",
                "entrepreneur_question_en": "How would you like this capital to be repaid?",
                "resource_question": "How is the capital repaid?",
                "resource_question_en": "How is the capital repaid?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Repayment",
                "short_name_en": "CD_Repayment",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Collateral",
            defaults={
                "entrepreneur_question": "What types of collateral (if any) do you have?",
                "entrepreneur_question_en": "What types of collateral (if any) do you have?",
                "resource_question": "What types of collateral do you require?",
                "resource_question_en": "What types of collateral do you require?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Collateral",
                "short_name_en": "CD_Collateral",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Disbursement",
            defaults={
                "entrepreneur_question": "How soon do you need the capital?",
                "entrepreneur_question_en": "How soon do you need the capital?",
                "resource_question": "How soon can the capital be disbursed?",
                "resource_question_en": "How soon can the capital be disbursed?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Disbursement",
                "short_name_en": "CD_Disbursement",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Use_of_Capital",
            defaults={
                "entrepreneur_question": "What do you need capital for?",
                "entrepreneur_question_en": "What do you need capital for?",
                "resource_question": "How should the company use your capital?",
                "resource_question_en": "How should the company use your capital?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Use_of_Capital",
                "short_name_en": "CD_Use_of_Capital",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Impact_Track_Record",
            defaults={
                "entrepreneur_question": "Does your business have an impact track record?",
                "entrepreneur_question_en": "Does your business have an impact track record?",
                "resource_question": "Does the business need to have an impact track record?",
                "resource_question_en": "Does the business need to have an impact track record?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Impact_Track_Record",
                "short_name_en": "CD_Impact_Track_Record",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Impact",
            defaults={
                "entrepreneur_question": "To what degree is generating impact a part of your business model?",
                "entrepreneur_question_en": "To what degree is generating impact a part of your business model?",
                "resource_question": "What degree of impact embeddedness are you looking for?",
                "resource_question_en": "What degree of impact embeddedness are you looking for?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Impact",
                "short_name_en": "CD_Impact",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Growth_Projections",
            defaults={
                "entrepreneur_question": "What is your company's growth projection?",
                "entrepreneur_question_en": "What is your company's growth projection?",
                "resource_question": "What should companies' growth projections look like?",
                "resource_question_en": "What should companies' growth projections look like?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Growth_Projections",
                "short_name_en": "CD_Growth_Projections",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Profit_Margins",
            defaults={
                "entrepreneur_question": "How would you describe your company's profit margins?",
                "entrepreneur_question_en": "How would you describe your company's profit margins?",
                "resource_question": "What should the company's profit margins look like?",
                "resource_question_en": "What should the company's profit margins look like?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Profit_Margins",
                "short_name_en": "CD_Profit_Margins",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Historical_Rev",
            defaults={
                "entrepreneur_question": "How long have you been generating revenue?",
                "entrepreneur_question_en": "How long have you been generating revenue?",
                "resource_question": "How long ago should the company have started generating revenue?",
                "resource_question_en": "How long ago should the company have started generating revenue?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Historical_Rev",
                "short_name_en": "CD_Historical_Rev",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Rev_Recurrence",
            defaults={
                "entrepreneur_question": "Are you generating revenue? If so, how recurrent are your revenues?",
                "entrepreneur_question_en": "Are you generating revenue? If so, how recurrent are your revenues?",
                "resource_question": "How recurrent would you like the company's revenues to be?",
                "resource_question_en": "How recurrent would you like the company's revenues to be?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Rev_Recurrence",
                "short_name_en": "CD_Rev_Recurrence",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Company_Stage",
            defaults={
                "entrepreneur_question": "How would you describe your company's current stage of maturity?",
                "entrepreneur_question_en": "How would you describe your company's current stage of maturity?",
                "resource_question": "What stages of maturity are you interested in?",
                "resource_question_en": "What stages of maturity are you interested in?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Company_Stage",
                "short_name_en": "CD_Company_Stage",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )
        Question.objects.update_or_create(
            slug="CD_Legal_Registration",
            defaults={
                "entrepreneur_question": "How is your business legally registered?",
                "entrepreneur_question_en": "How is your business legally registered?",
                "resource_question": "What types of organizations are you interested in?",
                "resource_question_en": "What types of organizations are you interested in?",
                "ttl": datetime.timedelta(days=1000),
                "short_name": "CD_Legal_Registration",
                "short_name_en": "CD_Legal_Registration",
                "question_type_id": 2,
                "question_category_id": capital_category.pk,
            }
        )

        questions_map = {q.slug: q.pk for q in Question.objects.all()}

        Answer.objects.filter(question__question_category__name="Capital Structures").delete()

        Answer.objects.bulk_create([
            Answer(
                **{
                    "value": "For-profit",
                    "value_en": "For-profit",
                    "question_id": questions_map["CD_Legal_Registration"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Concept stage",
                    "value_en": "Concept stage",
                    "question_id": questions_map["CD_Company_Stage"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Pre-revenue",
                    "value_en": "Pre-revenue",
                    "question_id": questions_map["CD_Rev_Recurrence"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "0 year (pre-revenue)",
                    "value_en": "0 year (pre-revenue)",
                    "question_id": questions_map["CD_Historical_Rev"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "We are unsure how much we will be able to generate",
                    "value_en": "We are unsure how much we will be able to generate",
                    "question_id": questions_map["CD_Profit_Margins"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Livelihood enterprise",
                    "value_en": "Livelihood enterprise",
                    "question_id": questions_map["CD_Growth_Projections"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Generating impact is core to our model",
                    "value_en": "Generating impact is core to our model",
                    "question_id": questions_map["CD_Impact"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "My business does not have (and will not have) an impact track record",
                    "value_en": "My business does not have (and will not have) an impact track record",
                    "question_id": questions_map["CD_Impact_Track_Record"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Proof of concept",
                    "value_en": "Proof of concept",
                    "question_id": questions_map["CD_Use_of_Capital"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "< 6 weeks",
                    "value_en": "< 6 weeks",
                    "question_id": questions_map["CD_Disbursement"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Assets",
                    "value_en": "Assets",
                    "question_id": questions_map["CD_Collateral"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Third party exit",
                    "value_en": "Third party exit",
                    "question_id": questions_map["CD_Repayment"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "0 - 1 Year",
                    "value_en": "0 - 1 Year",
                    "question_id": questions_map["CD_Repayment_Timeline"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Dilutive",
                    "value_en": "Dilutive",
                    "question_id": questions_map["CD_Dilution"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "High",
                    "value_en": "High",
                    "question_id": questions_map["CD_Funder_Involvement"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Africa",
                    "value_en": "Africa",
                    "question_id": questions_map["CD_Geography"],
                    "order": 1,
                }
            ),
            Answer(
                **{
                    "value": "Non-profit",
                    "value_en": "Non-profit",
                    "question_id": questions_map["CD_Legal_Registration"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Early stage",
                    "value_en": "Early stage",
                    "question_id": questions_map["CD_Company_Stage"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Low predictability",
                    "value_en": "Low predictability",
                    "question_id": questions_map["CD_Rev_Recurrence"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "0-2 years",
                    "value_en": "0-2 years",
                    "question_id": questions_map["CD_Historical_Rev"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "We predict we'll have a >30% profit margin",
                    "value_en": "We predict we'll have a >30% profit margin",
                    "question_id": questions_map["CD_Profit_Margins"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Dynamic enterprise",
                    "value_en": "Dynamic enterprise",
                    "question_id": questions_map["CD_Growth_Projections"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Some aspects of our model are focused on generating impact",
                    "value_en": "Some aspects of our model are focused on generating impact",
                    "question_id": questions_map["CD_Impact"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "I have a plan to measure impact and develop an impact track record",
                    "value_en": "I have a plan to measure impact and develop an impact track record",
                    "question_id": questions_map["CD_Impact_Track_Record"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Assets",
                    "value_en": "Assets",
                    "question_id": questions_map["CD_Use_of_Capital"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "> 6 weeks",
                    "value_en": "> 6 weeks",
                    "question_id": questions_map["CD_Disbursement"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Invoices/Purchase orders",
                    "value_en": "Invoices/Purchase orders",
                    "question_id": questions_map["CD_Collateral"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Internal cash flows",
                    "value_en": "Internal cash flows",
                    "question_id": questions_map["CD_Repayment"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "2 - 6 Years",
                    "value_en": "2 - 6 Years",
                    "question_id": questions_map["CD_Repayment_Timeline"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Non-dilutive",
                    "value_en": "Non-dilutive",
                    "question_id": questions_map["CD_Dilution"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Low",
                    "value_en": "Low",
                    "question_id": questions_map["CD_Funder_Involvement"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "East Asia & Pacific",
                    "value_en": "East Asia & Pacific",
                    "question_id": questions_map["CD_Geography"],
                    "order": 2,
                }
            ),
            Answer(
                **{
                    "value": "Shared Ownership",
                    "value_en": "Shared Ownership",
                    "question_id": questions_map["CD_Legal_Registration"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Growth stage",
                    "value_en": "Growth stage",
                    "question_id": questions_map["CD_Company_Stage"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Seasonal",
                    "value_en": "Seasonal",
                    "question_id": questions_map["CD_Rev_Recurrence"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "2-5 years",
                    "value_en": "2-5 years",
                    "question_id": questions_map["CD_Historical_Rev"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "We predict we'll have a <30% profit margin",
                    "value_en": "We predict we'll have a <30% profit margin",
                    "question_id": questions_map["CD_Profit_Margins"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Niche enterprise",
                    "value_en": "Niche enterprise",
                    "question_id": questions_map["CD_Growth_Projections"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Others do not describe our venture as impact-driven",
                    "value_en": "Others do not describe our venture as impact-driven",
                    "question_id": questions_map["CD_Impact"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "I have measured impact and have an impact track record I can share with capital providers",
                    "value_en": "I have measured impact and have an impact track record I can share with capital providers",
                    "question_id": questions_map["CD_Impact_Track_Record"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Working capital",
                    "value_en": "Working capital",
                    "question_id": questions_map["CD_Use_of_Capital"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Revenues",
                    "value_en": "Revenues",
                    "question_id": questions_map["CD_Collateral"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Future funding",
                    "value_en": "Future funding",
                    "question_id": questions_map["CD_Repayment"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "7 - 10 Years",
                    "value_en": "7 - 10 Years",
                    "question_id": questions_map["CD_Repayment_Timeline"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "South Asia",
                    "value_en": "South Asia",
                    "question_id": questions_map["CD_Geography"],
                    "order": 3,
                }
            ),
            Answer(
                **{
                    "value": "Scaling",
                    "value_en": "Scaling",
                    "question_id": questions_map["CD_Company_Stage"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Recurring/Repeatable",
                    "value_en": "Recurring/Repeatable",
                    "question_id": questions_map["CD_Rev_Recurrence"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "5+ years",
                    "value_en": "5+ years",
                    "question_id": questions_map["CD_Historical_Rev"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Our profit margin is below 30%",
                    "value_en": "Our profit margin is below 30%",
                    "question_id": questions_map["CD_Profit_Margins"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Category pioneer",
                    "value_en": "Category pioneer",
                    "question_id": questions_map["CD_Growth_Projections"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Growth capital",
                    "value_en": "Growth capital",
                    "question_id": questions_map["CD_Use_of_Capital"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Equity funding",
                    "value_en": "Equity funding",
                    "question_id": questions_map["CD_Collateral"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Product",
                    "value_en": "Product",
                    "question_id": questions_map["CD_Repayment"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "None - No payback required",
                    "value_en": "None - No payback required",
                    "question_id": questions_map["CD_Repayment_Timeline"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Middle East and Central Asia",
                    "value_en": "Middle East and Central Asia",
                    "question_id": questions_map["CD_Geography"],
                    "order": 4,
                }
            ),
            Answer(
                **{
                    "value": "Established",
                    "value_en": "Established",
                    "question_id": questions_map["CD_Company_Stage"],
                    "order": 5,
                }
            ),
            Answer(
                **{
                    "value": "Our profit margin is around or above 30%",
                    "value_en": "Our profit margin is around or above 30%",
                    "question_id": questions_map["CD_Profit_Margins"],
                    "order": 5,
                }
            ),
            Answer(
                **{
                    "value": "High growth venture",
                    "value_en": "High growth venture",
                    "question_id": questions_map["CD_Growth_Projections"],
                    "order": 5,
                }
            ),
            Answer(
                **{
                    "value": "No collateral available",
                    "value_en": "No collateral available",
                    "question_id": questions_map["CD_Collateral"],
                    "order": 5,
                }
            ),
            Answer(
                **{
                    "value": "None - No payback required",
                    "value_en": "None - No payback required",
                    "question_id": questions_map["CD_Repayment"],
                    "order": 5,
                }
            ),
            Answer(
                **{
                    "value": "Central and Eastern Europe",
                    "value_en": "Central and Eastern Europe",
                    "question_id": questions_map["CD_Geography"],
                    "order": 5,
                }
            ),
            Answer(
                **{
                    "value": "Western Europe",
                    "value_en": "Western Europe",
                    "question_id": questions_map["CD_Geography"],
                    "order": 6,
                }
            ),
            Answer(
                **{
                    "value": "Latin America and the Caribbean",
                    "value_en": "Latin America and the Caribbean",
                    "question_id": questions_map["CD_Geography"],
                    "order": 7,
                }
            ),
            Answer(
                **{
                    "value": "North America",
                    "value_en": "North America",
                    "question_id": questions_map["CD_Geography"],
                    "order": 8,
                }
            ),
        ])

        sources_map = {s.name: s.pk for s in FundingSource.objects.all()}
        answers_map = {f'{a.question.slug}|{a.order}': a.pk for a in Answer.objects.filter(question__question_category__name="Capital Structures")}

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Legal_Registration",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Company_Stage",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Company_Stage",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Rev_Recurrence",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Rev_Recurrence",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Historical_Rev",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Historical_Rev",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Profit_Margins",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Profit_Margins",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Growth_Projections",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Use_of_Capital",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Disbursement",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|1"], answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Repayment_Timeline",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|1"], answers_map["CD_Repayment_Timeline|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Use_of_Capital",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Dilution",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Funder_Involvement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenue-Based Loans - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenue-Based Loans"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Collateral",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|1"], answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|1"], answers_map["CD_Repayment_Timeline|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Venture Debt - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Venture Debt"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Legal_Registration",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Company_Stage",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Growth_Projections",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Use_of_Capital",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Company_Stage",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Historical_Rev",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Legal_Registration",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Company_Stage",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Use_of_Capital",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Disbursement",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|1"], answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Repayment",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Repayment_Timeline",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Dilution",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Profit_Margins",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Growth_Projections",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Use_of_Capital",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Disbursement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Funder_Involvement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Prizes - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Prizes"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|1"], answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|2"], answers_map["CD_Repayment_Timeline|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Redeemable Equity - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Redeemable Equity"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Company_Stage",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Impact",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Impact_Track_Record",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Use_of_Capital",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Use_of_Capital",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Repayment",
                "criteria_weight_id": 3,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Repayment_Timeline",
                "criteria_weight_id": 3,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Dilution",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Funder_Involvement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Traditional Grant - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Traditional Grant"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Company_Stage",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Rev_Recurrence",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Historical_Rev",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Profit_Margins",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Use_of_Capital",
                "criteria_weight_id": 3,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Collateral",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Repayment_Timeline",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|1"], answers_map["CD_Repayment_Timeline|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Dilution",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Funder_Involvement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Secured Debt - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Secured Debt"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Company_Stage",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Rev_Recurrence",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Historical_Rev",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Profit_Margins",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Collateral",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Repayment",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Repayment_Timeline",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Dilution",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Funder_Involvement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Supply Chain Financing - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Supply Chain Financing"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Legal_Registration",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Company_Stage",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Rev_Recurrence",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Historical_Rev",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Profit_Margins",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Growth_Projections",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Use_of_Capital",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Collateral",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|1"], answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Company_Stage",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Rev_Recurrence",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Historical_Rev",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Profit_Margins",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Use_of_Capital",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Disbursement",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|1"], answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Repayment",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Repayment_Timeline",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Dilution",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Funder_Involvement",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Revenues - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Revenues"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|1"], answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "SME Mezzanine Debt - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["SME Mezzanine Debt"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Legal_Registration",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Company_Stage",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Impact",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Impact_Track_Record",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Use_of_Capital",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|1"], answers_map["CD_Repayment_Timeline|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Recoverable Grants - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Recoverable Grants"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Company_Stage",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Impact",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Impact_Track_Record",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Use_of_Capital",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Forgivable Loans - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Forgivable Loans"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Legal_Registration",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Company_Stage",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Growth_Projections",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Impact",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Impact_Track_Record",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Use_of_Capital",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Funder_Involvement",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|1"], answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Convertible Grants - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Convertible Grants"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Company_Stage",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Rev_Recurrence",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Historical_Rev",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Profit_Margins",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Use_of_Capital",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Collateral",
                "criteria_weight_id": 3,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Debt Crowdfunding - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Debt Crowdfunding"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Legal_Registration",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Company_Stage",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Growth_Projections",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Use_of_Capital",
                "criteria_weight_id": 3,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Disbursement",
                "criteria_weight_id": 4,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Equity Crowdfunding - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Equity Crowdfunding"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Legal_Registration",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Legal_Registration"],
            }
        ).answers.set([answers_map["CD_Legal_Registration|1"], answers_map["CD_Legal_Registration|2"], answers_map["CD_Legal_Registration|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Company_Stage",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Company_Stage"],
            }
        ).answers.set([answers_map["CD_Company_Stage|1"], answers_map["CD_Company_Stage|2"], answers_map["CD_Company_Stage|3"], answers_map["CD_Company_Stage|4"], answers_map["CD_Company_Stage|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Rev_Recurrence",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Rev_Recurrence"],
            }
        ).answers.set([answers_map["CD_Rev_Recurrence|1"], answers_map["CD_Rev_Recurrence|2"], answers_map["CD_Rev_Recurrence|3"], answers_map["CD_Rev_Recurrence|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Historical_Rev",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Historical_Rev"],
            }
        ).answers.set([answers_map["CD_Historical_Rev|1"], answers_map["CD_Historical_Rev|2"], answers_map["CD_Historical_Rev|3"], answers_map["CD_Historical_Rev|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Profit_Margins",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Profit_Margins"],
            }
        ).answers.set([answers_map["CD_Profit_Margins|1"], answers_map["CD_Profit_Margins|2"], answers_map["CD_Profit_Margins|3"], answers_map["CD_Profit_Margins|4"], answers_map["CD_Profit_Margins|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Growth_Projections",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Growth_Projections"],
            }
        ).answers.set([answers_map["CD_Growth_Projections|1"], answers_map["CD_Growth_Projections|2"], answers_map["CD_Growth_Projections|3"], answers_map["CD_Growth_Projections|4"], answers_map["CD_Growth_Projections|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Impact",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Impact"],
            }
        ).answers.set([answers_map["CD_Impact|1"], answers_map["CD_Impact|2"], answers_map["CD_Impact|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Impact_Track_Record",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Impact_Track_Record"],
            }
        ).answers.set([answers_map["CD_Impact_Track_Record|1"], answers_map["CD_Impact_Track_Record|2"], answers_map["CD_Impact_Track_Record|3"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Use_of_Capital",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Use_of_Capital"],
            }
        ).answers.set([answers_map["CD_Use_of_Capital|1"], answers_map["CD_Use_of_Capital|2"], answers_map["CD_Use_of_Capital|3"], answers_map["CD_Use_of_Capital|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Disbursement",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Disbursement"],
            }
        ).answers.set([answers_map["CD_Disbursement|1"], answers_map["CD_Disbursement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Collateral",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Collateral"],
            }
        ).answers.set([answers_map["CD_Collateral|1"], answers_map["CD_Collateral|2"], answers_map["CD_Collateral|3"], answers_map["CD_Collateral|4"], answers_map["CD_Collateral|5"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Repayment",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Repayment"],
            }
        ).answers.set([answers_map["CD_Repayment|4"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Repayment_Timeline",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Repayment_Timeline"],
            }
        ).answers.set([answers_map["CD_Repayment_Timeline|1"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Dilution",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Dilution"],
            }
        ).answers.set([answers_map["CD_Dilution|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Funder_Involvement",
                "criteria_weight_id": 5,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Funder_Involvement"],
            }
        ).answers.set([answers_map["CD_Funder_Involvement|2"]])

        FundingCriteria.objects.create(
            **{
                "name": "Rewards Crowdfunding - CD_Geography",
                "criteria_weight_id": 1,
                "funding_source_id": sources_map["Rewards Crowdfunding"],
                "question_id": questions_map["CD_Geography"],
            }
        ).answers.set([answers_map["CD_Geography|1"], answers_map["CD_Geography|2"], answers_map["CD_Geography|3"], answers_map["CD_Geography|4"], answers_map["CD_Geography|5"], answers_map["CD_Geography|6"], answers_map["CD_Geography|7"], answers_map["CD_Geography|8"]])
