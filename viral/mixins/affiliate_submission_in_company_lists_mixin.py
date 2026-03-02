from django.db.models import Q
from viral.models import Affiliate, Company
from company_lists.models import CompanyList


class AffiliateSubmissionInCompanyListsMixin:
    """
    A mixin that automates adding a company, that submitted an Affiliate,
    into the company lists that are linked with that same Affiliate.
    """

    def populate_affiliate_company_lists(self, affiliate: Affiliate, company: Company) -> None:
        # Include:
        # - lists explicitly linked to this affiliate via `Affiliate.company_lists`
        # - the auto-created "Affiliate Submissions" smart list (`CompanyList.affiliate`)
        linked_lists = affiliate.company_lists.all()
        smart_list = CompanyList.objects.filter(
            company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS,
            affiliate=affiliate,
        )

        candidate_lists = CompanyList.objects.filter(
            Q(pk__in=linked_lists.values("pk")) | Q(pk__in=smart_list.values("pk"))
        ).distinct()

        # NOTE: Avoid `exclude(companies__pk=...)` on an M2M: it can drop lists that have
        # zero companies due to INNER JOIN semantics. Using a pk-subquery preserves empty lists.
        company_lists_to_populate = candidate_lists.exclude(
            pk__in=candidate_lists.filter(companies__pk=company.pk).values("pk")
        )

        # Only (easy) way to bulk create/update m2m fields:
        through_model = CompanyList.companies.through
        through_model.objects.bulk_create([
            through_model(companylist_id=pk, company_id=company.pk)
            for pk in company_lists_to_populate.values_list('pk', flat=True)],
            ignore_conflicts=True)
