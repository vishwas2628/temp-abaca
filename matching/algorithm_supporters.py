from matching.models import InterestedCTA, MatchingTotalScores
from viral.models import Company, UserProfile, AffiliateProgramEntry, Affiliate, Network
from grid.models import Assessment

from django.db.models import Q, Subquery, OuterRef
from allauth.account.models import EmailAddress


def getMatchesSupporter(supporter, page=1, per_page=12, match_exclusions=None, match_filters=None):
    """
    Get all possible matches for the current Supporter

    TODO: Add link here for matching algorithm technical documentation
    """
    # Paginate the Entrepreneurs for performance reasons and to match the UX requirements
    # on the front-end
    offset = (page - 1) * per_page

    verified_subquery = Subquery(EmailAddress.objects.filter(user__userprofile__company=OuterRef('company_id')).values('verified')[:1])

    matching_scores = MatchingTotalScores.objects.annotate(verified=verified_subquery).filter(
        supporter_id=supporter.id, verified=True).exclude(max_score_percentil=0).order_by('-max_score_percentil').distinct()

    # Check if need to filter matches
    if match_filters:
        filter_list = Q()

        for item in match_filters:
            query_filters = item['queries']
            include_any = item['options']['any']

            for query_filter in query_filters:
                if include_any:
                    filter_list |= Q(**query_filter)
                else:
                    filter_list &= Q(**query_filter)

        if filter_list:
            filtered_company_ids = Company.objects.filter(
                filter_list).values_list('pk')
            matching_scores = matching_scores.filter(
                company_id__in=filtered_company_ids)

    # Check if we need to exclude matches that have some type of connection
    if match_exclusions:
        if 'connections' in match_exclusions:
            excluded_entrepreneurs = InterestedCTA.objects.values_list('entrepreneur').filter(
                supporter=supporter.user_profile.company_id).exclude(
                state_of_interest=InterestedCTA.INITIAL_VALUE).values_list('entrepreneur_id')
            matching_scores = matching_scores.exclude(
                company_id__in=excluded_entrepreneurs)
        if 'score_minimum' in match_exclusions:
            score_minimum = match_exclusions['score_minimum']
            matching_scores = matching_scores.exclude(
                max_score_percentil__lt=score_minimum)
    else:
        matching_scores = matching_scores.all()

    paginated_scores = matching_scores[offset:offset +
                                       per_page].values('company_id', 'max_score_percentil')

    # Initialise the results, that will consist on a tuple with the entrepreneur, and the
    # score percentage
    results = []

    # Grab all the needed entrepreneur data for performance reasons
    entrep_companies = Company.objects.prefetch_related('locations').prefetch_related(
        'sectors', 'sectors__groups').prefetch_related(
        'networks', 'networks__locations').filter(
        pk__in=paginated_scores.values_list('company_id'))
    entrep_latest_assessments = Assessment.objects.select_related('level').filter(
        evaluated__in=paginated_scores.values_list('company_id')).order_by(
        'evaluated', '-created_at').distinct('evaluated')

    for score in paginated_scores:
        entrepreneur = next(
            (company for company in entrep_companies if company.id == score['company_id']), None)

        if not entrepreneur:
            # If no entrepreneur is found, skip it from final results
            continue

        assessment = next(
            (assessment for assessment in entrep_latest_assessments if assessment.evaluated == entrepreneur.id), None)
        assessment_level = assessment.level.value if assessment is not None else 1

        affiliate_entries = []

        try:
            """
            Fetch all affiliate submissions associated with supporters.
            Supporters are associated with submissions if:
            a) They are tagged in the affiliate as a Supporter.
            b) They are members of a network associated with the affiliate.
            """
            
            supporter_company = supporter.user_profile.company
            by_supporter_affiliates = Q(affiliate__supporters__id=supporter.id) | Q(
                affiliate__networks__in=supporter_company.networks.all())
            affiliate_entries = AffiliateProgramEntry.objects.filter(by_supporter_affiliates, 
                user_profile__company=entrepreneur.id).order_by('-updated_at')
            
        except AffiliateProgramEntry.DoesNotExist:
            pass

        results.append({
            'company': entrepreneur,
            'affiliates': affiliate_entries,
            'level': assessment_level,
            'score': score['max_score_percentil']
        })

    return results


def getSupporterInterestMatches(supporter, interests, match_filters=None):
    # Initialise the results, that will consist on a tuple with the supporter, and the
    # score percentage
    results = []

    # Grab all the needed supporter data for performance reasons
    entrepreneurs_of_interest = Company.objects.prefetch_related('locations').prefetch_related(
        'sectors', 'sectors__groups').prefetch_related(
        'networks', 'networks__locations').filter(
        pk__in=interests.values_list('entrepreneur'))

    latest_assessments = Assessment.objects.select_related('level').filter(
        evaluated__in=interests.values_list('entrepreneur')).order_by('evaluated', '-created_at').distinct('evaluated')

    matching_scores = MatchingTotalScores.objects.filter(
        supporter_id=supporter.id, company_id__in=entrepreneurs_of_interest.values_list('id')).values(
        'company_id', 'max_score_percentil').order_by("-max_score_percentil").distinct()

    if match_filters:
        filter_list = Q()

        for item in match_filters:
            query_filters = item['queries']
            include_any = item['options']['any']

            for query_filter in query_filters:
                if include_any:
                    filter_list |= Q(**query_filter)
                else:
                    filter_list &= Q(**query_filter)

        entrepreneurs_of_interest = entrepreneurs_of_interest.filter(
            filter_list)

    # Include all interests independently if they are a match
    for company in entrepreneurs_of_interest:
        match_score = next(
            (score['max_score_percentil'] for score in matching_scores if company.id == score['company_id']), 0)

        assessment = next(
            (assessment for assessment in latest_assessments if assessment.evaluated == company.id), None)
        assessment_level = assessment.level.value if assessment is not None else 1

        affiliate_entries = []

        try:
            user_profile = UserProfile.objects.get(company_id=company.id)

            # Fetch all affiliate associated with supporter
            affiliates = Affiliate.objects.filter(supporters__id=supporter.id)

            affiliate_entries = AffiliateProgramEntry.objects.filter(
                user_profile=user_profile, affiliate__in=affiliates).order_by('-updated_at')
        except (UserProfile.DoesNotExist, Affiliate.DoesNotExist, AffiliateProgramEntry.DoesNotExist):
            pass

        results.append({
            'company': company,
            'affiliates': affiliate_entries,
            'level': assessment_level,
            'score': match_score,
        })

    # Order results descending by score
    results.sort(key=lambda item: item["score"], reverse=True)

    return results


def getSupporterMatchByCompany(supporter, company):
    """
    Fetch a match for a Supporter by company
    """
    matching_score = MatchingTotalScores.objects.filter(
        company_id=company.id, supporter_id=supporter.id).first()

    if not matching_score:
        return None

    latest_assessment = Assessment.objects.select_related('level').filter(
        evaluated=matching_score.company_id).order_by('evaluated', '-created_at').first()
    assessment_level = latest_assessment.level.value if latest_assessment != None else 1

    return {
        "company": company,
        "score": matching_score.max_score_percentil,
        "level": assessment_level
    }


def getMatchesForSupporterFromEntrepreneurs(supporter, companies=[]):
    """
    Fetch matches between a Supporter and a list of Entrepreneurs
    """
    if not len(companies):
        return None

    try:
        companies_pks = [company.pk or 0 for company in companies]
        matching_scores = MatchingTotalScores.objects.filter(
            company_id__in=companies_pks, supporter_id=supporter.pk)

        return list(map(lambda company: {
            'company': company,
            'score': next((score.max_score_percentil for score in matching_scores
                           if score.company_id == company.pk), None)
        }, companies))
    except MatchingTotalScores.DoesNotExist:
        return None
