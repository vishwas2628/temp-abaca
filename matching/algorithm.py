from viral.models import UserProfile
from matching.models import Response, Supporter, Criteria, QuestionType, InterestedCTA, MatchingTotalScores, SupporterOffering, Criteria
from functools import reduce
from django.db.models import Q, OuterRef, Subquery
from allauth.account.models import EmailAddress


def getMatches(user_profile, page=1, per_page=12, match_exclusions=None, match_filters=None):
    """
    Get all possible matches for the current Entrepreneur

    TODO: Add link here for matching algorithm technical documentation
    """

    # Paginate the Supporters for performance reasons and to match the UX requirements
    # on the front-end
    offset = (page - 1) * per_page

    verified_subquery = Subquery(EmailAddress.objects.filter(user__userprofile__supporter=OuterRef('supporter_id')).values('verified')[:1])

    matching_scores = MatchingTotalScores.objects.annotate(verified=verified_subquery).filter(
        company_id=user_profile.company_id, verified=True).exclude(max_score_percentil=0).order_by('-max_score_percentil').distinct()

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
            filtered_supporter_ids = Supporter.objects.filter(
                filter_list).values_list('pk')
            matching_scores = matching_scores.filter(
                supporter_id__in=filtered_supporter_ids)

    # Check if we need to exclude matches that have some type of connection
    if match_exclusions:
        if 'connections' in match_exclusions:
            current_interests = InterestedCTA.objects.values_list('supporter').filter(
                entrepreneur=user_profile.company_id).exclude(
                state_of_interest=InterestedCTA.INITIAL_VALUE)
            excluded_supporters = Supporter.objects.select_related('user_profile').filter(
                user_profile__company__in=current_interests).values_list('id')
            matching_scores = matching_scores.exclude(
                supporter_id__in=excluded_supporters)
        if 'score_minimum' in match_exclusions:
            score_minimum = match_exclusions['score_minimum']
            matching_scores = matching_scores.exclude(
                max_score_percentil__lt=score_minimum)
    else:
        matching_scores = matching_scores.all()

    paginated_scores = matching_scores[offset:offset +
                                       per_page].values('supporter_id', 'max_score_percentil')

    # Initialise the results, that will consist on a tuple with the supporter, and the
    # score percentage
    results = []

    # Grab all the needed supporter data for performance reasons
    supporters = Supporter.objects.select_related('user_profile').prefetch_related(
        'user_profile__company', 'user_profile__company__locations', 'user_profile__company__sectors',
        'user_profile__company__networks').prefetch_related('types').prefetch_related(
        'sectors', 'sectors__groups').prefetch_related('locations').filter(
        pk__in=paginated_scores.values_list('supporter_id'))

    for score in paginated_scores:
        supporter = next(
            (supporter for supporter in supporters if supporter.id == score['supporter_id']), None)

        if supporter:
            results.append({
                'supporter': supporter,
                'score': score['max_score_percentil']
            })

    return results


def getEntrepreneurInterestMatches(company, interests, match_filters=None):
    """
    Fetch matches for an Entrepreneur based on his interests
    """
    # Get the Profile of the Company
    try:
        user_profile = UserProfile.objects.get(company=company)
    except UserProfile.DoesNotExist:
        return None

    # Initialise the results, that will consist on a tuple with the supporter, and the
    # score percentage
    results = []

    # Grab all the needed supporter data for performance reasons
    supporters_of_interest = Supporter.objects.select_related('user_profile').prefetch_related(
        'user_profile__company', 'user_profile__company__locations', 'user_profile__company__sectors',
        'user_profile__company__networks').prefetch_related('types').prefetch_related('sectors').prefetch_related(
        'locations').filter(
        user_profile__company__in=interests.values_list('supporter'))
    matching_scores = MatchingTotalScores.objects.filter(
        company_id=user_profile.company_id, supporter_id__in=supporters_of_interest.values_list('id')).values(
        'supporter_id', 'max_score_percentil').order_by("-max_score_percentil").distinct()

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

        supporters_of_interest = supporters_of_interest.filter(
            filter_list)

    # Include all interests independently if they are a match
    for supporter in supporters_of_interest:
        match_score = next(
            (score['max_score_percentil'] for score in matching_scores if supporter.id == score['supporter_id']), 0)

        results.append({
            'supporter': supporter,
            'score': match_score
        })

    # Order results descending by score
    results.sort(key=lambda item: item["score"], reverse=True)

    return results


def getEntrepreneurMatchByCompany(user_profile, match_profile):
    """
    Fetch a match for a Entrepreneur by company
    """
    try:
        supporter = Supporter.objects.select_related('user_profile').prefetch_related(
            'user_profile__company', 'user_profile__company__locations', 'user_profile__company__sectors',
            'user_profile__company__networks').prefetch_related('types').prefetch_related('sectors').prefetch_related(
            'locations').get(
            user_profile=match_profile)
    except Supporter.DoesNotExist:
        return None

    matching_score = MatchingTotalScores.objects.filter(
        company_id=user_profile.company_id, supporter_id=supporter.id).first()

    if not matching_score:
        return None

    return {
        'supporter': supporter,
        'score': matching_score.max_score_percentil
    }


def getMatchesForEntrepreneurFromSupporters(entrep_profile, supporters=[]):
    """
    Fetch matches between an Entrepreneur and a list of Supporters
    """
    if not len(supporters):
        return None

    try:
        supporters_pks = [supporter.pk or 0 for supporter in supporters]
        matching_scores = MatchingTotalScores.objects.filter(
            company_id=entrep_profile.company_id, supporter_id__in=supporters_pks)

        return list(map(lambda supporter: {
            'supporter': supporter,
            'score': next((score.max_score_percentil for score in matching_scores
                           if score.supporter_id == supporter.pk), None)
        }, supporters))
    except MatchingTotalScores.DoesNotExist:
        return None
