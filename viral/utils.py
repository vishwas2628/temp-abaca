import binascii
import os
import re
from datetime import datetime, time, timedelta

import bugsnag
import gspread
import requests
from allauth.account.models import EmailAddress
from django.contrib.admin.utils import flatten
from django.contrib.auth.models import User
from django.core import signing
from gspread.exceptions import APIError
from rest_auth.models import TokenModel
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

import settings
from grid.models import Assessment, Category
from matching.algorithm_supporters import getSupporterMatchByCompany
from sdg.models.sdg_affiliate_program_entry import SDGAffiliateProgramEntry
from shared.models import Logs
from viral.models import AdminTokens, Affiliate, AffiliateProgramEntry, Company, UserProfile, Vendor


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = dict()
        try:
            response.data['errors'] = exc.get_full_details()
        except AttributeError:
            response.data['errors'] = {}
        response.data['status_code'] = response.status_code
    return response


def save_assessment_to_spreadsheet(scores, company, email, viral_level, affiliate, hash_token, **kwargs):
    try:
        spreadsheet = get_affiliate_spreadsheet(affiliate)
        if not spreadsheet:
            return False

        worksheet = spreadsheet.sheet1 or spreadsheet.add_worksheet('Sheet1', 1, 1)

        top_row = worksheet.row_values(1)

        if len(top_row) == 0:
            worksheet.append_row(
                [
                    'Company name',
                    'Registration Email',
                    'Website',
                    'Activity Sectors',
                    'Continent',
                    'Country Code',
                    'Country',
                    'Region',
                    'City',
                    'VIRAL Level',
                    *[category.name for category in Category.objects.filter(group=2).order_by('order')],
                    'Share URL',
                    'Submitted date',
                    'Profile',
                    'Assessment Status',
                ]
            )
            top_row = worksheet.row_values(1)

        levels = {category.pk: 0 for category in Category.objects.filter(group=2).order_by('order')}
        for score in scores:
            if score['level'] and score['category'].pk in levels:
                levels[score['category'].pk] = score['level'].value

        row = [
            company.name,
            email,
            company.website,
            ','.join(map(lambda sector: sector.name, company.sectors.all())),
        ]

        location = company.locations.first()
        if len(top_row) >= 5 and top_row[4] == 'Continent':
            row += [
                location.continent if location else '',
                location.country_code if location else '',
                location.country if location else '',
                location.region if location else '',
                location.city if location else '',
            ]
        else:
            row.append(location.formatted_address if location else '')

        row += [
            viral_level,
            *levels.values(),
            f'https://{os.getenv("APP_BASE_URL", "viral.vilcap.com")}/assessment/{hash_token}',
            datetime.now().strftime('%Y/%m/%d'),
            f'https://{os.getenv("APP_BASE_URL", "viral.vilcap.com")}/profile/v/{company.access_hash}',
            Assessment.ASSESSMENT_STATES[kwargs.get('state', Assessment.REGISTERED_USER_STATE)][-1],
        ]

        worksheet.append_row(row)

        # Share spreadsheet with Admin
        share_affiliate_spreadsheet(spreadsheet, affiliate)
    except Exception as exception:
        bugsnag.notify(exception)


def update_spreadsheet(affiliate, hash_token, **kwargs):
    try:
        spreadsheet = get_affiliate_spreadsheet(affiliate)
        if not spreadsheet:
            return None

        try:
            worksheet = spreadsheet.sheet1 or spreadsheet.add_worksheet('Sheet1', '1', '1')
            cell = worksheet.find(re.compile(hash_token))
            row_number = cell.row
        except gspread.CellNotFound as exception:
            bugsnag.notify(exception)
            # In case of error, just skip the rest.
            return None

        # Update submitted date
        submitted_cell = worksheet.find('Submitted date')
        date_now = datetime.now().strftime('%Y/%m/%d')
        worksheet.update_cell(row_number, submitted_cell.col, date_now)

        # Update viral level
        viral_level = kwargs.get('viral_level')
        viral_level_cell = worksheet.find('VIRAL Level')
        if viral_level:
            worksheet.update_cell(row_number, viral_level_cell.col, viral_level)

        # Update score levels
        scores = kwargs.get('scores')
        if scores:
            for index, score in enumerate(scores, 1):
                level_column = viral_level_cell.col + index
                level_value = score['level'].value if score['level'] else 0
                worksheet.update_cell(row_number, level_column, level_value)

        # Update assessment state
        assessment_state_id = kwargs.get('state', Assessment.REGISTERED_USER_STATE)
        if assessment_state_id:
            status_cell = worksheet.find('Assessment Status')
            assessment_state_name = Assessment.ASSESSMENT_STATES[assessment_state_id][-1]
            worksheet.update_cell(row_number, status_cell.col, assessment_state_name)
    except Exception as exception:
        bugsnag.notify(exception)


def build_login_user(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
        email_address_verified = EmailAddress.objects.filter(email__iexact=user.email, verified=True).exists()
    except UserProfile.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    token, _ = TokenModel.objects.get_or_create(user=user)
    response = {
        'key': token.key,
        'verified_account': email_address_verified,
        'user_profile_id': user_profile.id,
        'user': {'email': user.email},
    }
    return Response(response, status=status.HTTP_200_OK)


def get_usable_admin_token(user):
    random_key = binascii.hexlify(os.urandom(20)).decode()
    admin_token, created = AdminTokens.objects.get_or_create(user=user, defaults={'key': random_key})

    if not created and has_admin_token_expired(admin_token) == True:
        admin_token.delete()
        get_usable_admin_token(user)

    return admin_token


def has_admin_token_expired(token):
    date_now = datetime.now()
    token_creation_date = token.created_at
    token_expiration_date = token_creation_date + timedelta(minutes=60)

    return date_now > token_expiration_date


def validate_admin_token(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
    except (UserProfile.DoesNotExist, Company.DoesNotExist):
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        admin_token = AdminTokens.objects.get(user=user)

        """
        TODO: The "available" boolean field determines if the admin has already submitted
        a session and therefore to log in again as the same user it should generate a new token.

        The code below is commented since there's an issue when submitting a new admin session
        for the same user on the webapp with a new token
        """
        # if admin_token.available == False or has_admin_token_expired(admin_token) == True:
        if has_admin_token_expired(admin_token) == True:
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_200_OK)
    except AdminTokens.DoesNotExist:
        return Response(status=status.HTTP_403_FORBIDDEN)


def validate_loginas_admin(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
    except (UserProfile.DoesNotExist, Company.DoesNotExist):
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        admin_token = AdminTokens.objects.get(user=user)
        email_address_verified = EmailAddress.objects.filter(email__iexact=user.email, verified=True).exists()

        if has_admin_token_expired(admin_token) == True:
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(
            {
                'as_admin': True,
                'key': admin_token.key,
                'user_profile_id': user_profile.id,
                'verified_account': email_address_verified,
                'user': {'email': user.email},
            },
            status=status.HTTP_200_OK,
        )
    except AdminTokens.DoesNotExist:
        return Response(status=status.HTTP_403_FORBIDDEN)


def confirm_admin_login_session(access_hash):
    try:
        user_profile = UserProfile.objects.get(company__access_hash=access_hash)
        email_address_verified = EmailAddress.objects.filter(
            email__iexact=user_profile.user.email, verified=True
        ).exists()
        admin_token = AdminTokens.objects.get(user=user_profile.user)
        print("reached here")

        if has_admin_token_expired(admin_token) == True:
            return False

        # Update admin token availability
        admin_token.available = False
        admin_token.save()

        return {
            'as_admin': True,
            'key': admin_token.key,
            'user_profile_id': user_profile.id,
            'verified_account': email_address_verified,
            'user': {'email': user_profile.user.email},
        }
    except (AdminTokens.DoesNotExist, UserProfile.DoesNotExist, User.DoesNotExist):
        return False


def fetch_google_location(address='', place_id=''):
    base = 'https://maps.googleapis.com/maps/api/geocode/json?'

    params = 'sensor={sen}&key={key}'.format(sen=False, key='AIzaSyAq1HB__RCHgh2KHt4MfsYhUPDqqocgQzo')
    params += '&address=%s' % address if len(address) else ''
    params += '&place_id=%s' % place_id if len(place_id) else ''

    url = '{base}{params}'.format(base=base, params=params)

    response = requests.get(url)
    components = response.json()["results"]

    return components


def search_google_places(needle, only_types=['geocode']):
    base = 'https://maps.googleapis.com/maps/api/place/autocomplete/json?'
    key = os.getenv('GOOGLE_PLACES_KEY', None)

    params = 'input={needle}&key={key}'.format(needle=needle, key=key)
    url = '{base}{params}'.format(base=base, params=params)

    response = requests.get(url)
    results = response.json()
    predictions = results["predictions"] if results and "predictions" in results else []

    return [prediction for prediction in predictions if not set(prediction["types"]).isdisjoint(only_types)]


def send_user_assessment_to_vendors(user_profile, user_vendors, levels, latest_assessment):
    for user_vendor in user_vendors:
        vendor_user_id = user_vendor.user_id
        vendor = user_vendor.user_vendor

        if not bool(vendor.endpoint):
            bugsnag.notify(
                Exception(vendor.name + " does not have a valid endpoint"),
                meta_data={"context": {"vendor": vendor.name}},
            )
            continue

        company = user_profile.company
        sectors = ', '.join(map(lambda sector: sector.name, company.sectors.all()))
        location = company.locations.all()[0].formatted_address
        assessment_state = Assessment.ASSESSMENT_STATES[latest_assessment.state][-1]

        payload = {
            "CompanyName": company.name,
            "RegistrationEmail": company.email,
            "Website": company.website,
            "ActivitySectors": sectors,
            "Location": location,
            "VIRALLevel": latest_assessment.level.value,
            "ShareURL": 'https://'
            + os.getenv('APP_BASE_URL', 'my.abaca.app')
            + '/assessment/'
            + latest_assessment.hash_token,
            "Profile": 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app') + '/profile/v/' + company.access_hash,
            "AssessmentStatus": assessment_state,
            "SubmittedDate": latest_assessment.created_at.strftime('%Y/%m/%d %H:%M'),
            "id": vendor_user_id,
        }

        for level in levels:
            category_name = level['category'].name.title().split(" ")
            category_name = "".join(category_name)

            if level['level'] is not None:
                payload[category_name] = level['level'].value
            else:
                payload[category_name] = 0

        vendor_auth = None

        if vendor.auth_type == Vendor.BASIC_AUTH:
            uncrypted_auth_password = str(signing.loads(vendor.auth_password))
            vendor_auth = requests.auth.HTTPBasicAuth(vendor.auth_user, uncrypted_auth_password)

        try:
            # Either send a single object (loose schema) or default to an array with an object (loose list schema)
            data = payload if vendor.callback_schema == Vendor.LOOSE_SCHEMA else [payload]

            vendor_response = requests.post(vendor.endpoint, json=data, auth=vendor_auth)
            response_level = 'info' if vendor_response.ok else 'error'
            has_response = vendor_response.headers.get("Content-Type", "").strip().startswith("application/json")
            log_data = {
                'response': vendor_response.json() if has_response else None,
                'status': vendor_response.status_code,
                'headers': vendor_response.headers,
                'request': {
                    'url': vendor_response.request.url,
                    'headers': vendor_response.request.headers,
                    'method': vendor_response.request.method,
                    'body': vendor_response.request.body,
                },
            }
            Logs.objects.create(slug='vendor', level=response_level, log=log_data)
        except Exception as error:
            bugsnag.notify(Exception("Vendor failed its response."), meta_data={"context": {"error": error}})


def submit_affiliate_webhook(webhook, affiliate, user_profile, company):
    "TODO: Isolate logic below to easily reuse and extend this funcionality"

    # Fetch user's submitted question bundle
    try:
        program = (
            AffiliateProgramEntry.objects.select_related('assessment')
            .prefetch_related('responses')
            .filter(affiliate=affiliate, user_profile=user_profile)
            .order_by('-created_at')
            .first()
        )
    except AffiliateProgramEntry.DoesNotExist:
        error_message = "Affiliate ID - {affiliate_id} - Has no entry for User Profile ID - {user_profile_id}".format(
            affiliate_id=affiliate.id, user_profile_id=user_profile.id
        )
        Logs.objects.create(slug='webhook', level='error', log=error_message)

    # Parse company location and sectors
    company_location = company.locations.values(
        'formatted_address', 'latitude', 'longitude', 'city', 'region', 'region_abbreviation', 'country', 'continent'
    ).first()
    company_sectors = list(map(lambda sector: sector.name, company.sectors.all()))

    # Build initial data
    data = {
        'submission_ID': program.id,
        'submitted_at': datetime.now().strftime('%Y/%m/%d %H:%M'),
        'Abaca_ID': company.id,
        'Abaca_profile': 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app') + '/profile/v/' + company.access_hash,
        'affiliate_id': affiliate.id,
        'affiliate_name': affiliate.name,
        'company_uid': company.uid,
        'submission_uid': program.uid,
        'submission_link': f'{os.getenv("API_DOMAIN", "api.abaca.app")}/admin/viral/affiliateprogramentry/{program.id}',
        'company_name': company.name,
        'email': company.email,
        'website': company.website,
        'location': company_location,
        'sectors': company_sectors,
        'assessments': {},
        'questions': {},
    }

    # Add match score for the Supporter associated to the Affiliate flow
    if affiliate.supporters.count():
        supporter = affiliate.supporters.first()
        match_score = getSupporterMatchByCompany(supporter, company)
        data['match_score'] = round(match_score['score']) if match_score else 0

    # Add Viral Level Assessment
    assessment = program.assessment
    assessment_key = 'Venture Investment Level'
    viral_level = assessment.level.value if assessment else 0
    if assessment:
        data['assessments'][assessment_key] = {'Level': viral_level}
        for value in assessment.data:
            level = value.get('level', 0)
            category = Category.objects.get(pk=value.get('category'))

            if level and category:
                data['assessments'][assessment_key][category.name] = level

    # Add Question Bundles responses
    responses = program.responses.all()
    if responses.count():
        for response in responses.all():
            question_key = response.question.slug or response.question.id
            if response.answers.count():
                data['questions'][question_key] = list(
                    map(lambda answer: answer['value'], response.answers.values('value'))
                )
            else:
                data['questions'][question_key] = response.value

    # Submit the request to the webhook and store the response on the logs
    webhook_response = requests.post(webhook.url, json=data)
    response_level = 'info' if webhook_response.ok else 'error'
    log_data = {
        'status': webhook_response.status_code,
        'headers': webhook_response.headers,
        'request': {
            'url': webhook_response.request.url,
            'headers': webhook_response.request.headers,
            'method': webhook_response.request.method,
            'body': webhook_response.request.body,
        },
    }

    Logs.objects.create(slug='webhook', level=response_level, log=log_data)


def request_more_data_from_vendor(company):
    webhook_url = settings.WEBHOOKS.get('REQUEST_EXTERNAL_COMPANY_DATA', None)

    if not webhook_url:
        return

    company_type = dict(Company.USER_TYPE).get(company.type, None)

    data = {'uid': company.uid, 'name': company.name, 'website': company.website, 'type': company_type}

    webhook_response = requests.post(webhook_url, json=data)
    response_level = 'info' if webhook_response.ok else 'error'
    log_data = {
        'status': webhook_response.status_code,
        'headers': webhook_response.headers,
        'request': {
            'url': webhook_response.request.url,
            'headers': webhook_response.request.headers,
            'method': webhook_response.request.method,
            'body': webhook_response.request.body,
        },
    }

    Logs.objects.create(slug='webhook', level=response_level, log=log_data)


def get_affiliate_spreadsheet(affiliate):
    print("Getting affiliate spreadsheet")
    json_credentials = (
        'client_secret_development.json' if os.getenv('APP_ENV') in ['local', 'qa', 'dev'] else 'client_secret.json'
    )
    client = gspread.service_account(filename=json_credentials)
    try:
        spreadsheet = client.open_by_url(affiliate.spreadsheet)
        print('Spreadsheet found', spreadsheet)
    except (gspread.SpreadsheetNotFound, gspread.exceptions.NoValidUrlKeyFound):
        spreadsheet = client.create(f'Abaca Assessments for {affiliate.name}')
        affiliate.spreadsheet = f'https://docs.google.com/spreadsheets/d/{spreadsheet.id}'
        affiliate.save()
    except Exception as exception:
        bugsnag.notify(exception)
        return None

    return spreadsheet


def write_affiliate_assessments_worksheet(spreadsheet, affiliate):
    categories = Category.objects.filter(group=2).order_by('order')

    rows = [
        [
            'Company name',
            'Registration Email',
            'Website',
            'Activity Sectors',
            'Continent',
            'Country Code',
            'Country',
            'Region',
            'City',
            'VIRAL Level',
            *[category.name for category in categories],
            'Share URL',
            'Submitted date',
            'Profile',
            'Assessment Status',
        ]
    ]

    # Fetch the user profiles associated with the affiliate, and for each, fetch the assessment and build the rows
    assessments_data = []
    for user_profile in UserProfile.objects.filter(source=affiliate):

        # Fetch all the assessments for that profile
        assessments = Assessment.objects.filter(evaluated=user_profile.company.id, user=user_profile.user.id).order_by(
            'created_at'
        )

        for assessment in assessments:
            location = user_profile.company.locations.first()
            levels = {category.pk: 0 for category in categories}
            for score in assessment.data:
                if score['category'] in levels:
                    levels[score['category']] = score.get('level', 0) or 0

            row = [
                user_profile.company.name,
                user_profile.user.email,
                user_profile.company.website,
                ','.join(map(lambda sector: sector.name, user_profile.company.sectors.all())),
                location.continent if location else '',
                location.country_code if location else '',
                location.country if location else '',
                location.region if location else '',
                location.city if location else '',
                assessment.level.value,
                *levels.values(),
                f'https://{os.getenv("APP_BASE_URL", "viral.vilcap.com")}/assessment/{assessment.hash_token}',
                datetime.now().strftime('%Y/%m/%d'),
                f'https://{os.getenv("APP_BASE_URL", "viral.vilcap.com")}/profile/v/{user_profile.company.access_hash}',
                Assessment.ASSESSMENT_STATES[Assessment.REGISTERED_USER_STATE][-1],
            ]

            assessments_data.append({'created_at': assessment.created_at, 'row': row})

    # Sort the rows by the assesment created date and add them to the spreadsheet
    rows += [entry['row'] for entry in sorted(assessments_data, key=lambda item: item['created_at'])]

    worksheet = spreadsheet.sheet1
    worksheet.clear()
    worksheet.append_rows(rows)

    return True


def write_affiliate_submissions_worksheet(spreadsheet, affiliate):
    try:
        spreadsheet_generation_allowed = (
            affiliate.flow_target != Company.SUPPORTER and affiliate.flow_type != Affiliate.SELF_ASSESSMENT
        )
        if not spreadsheet_generation_allowed:
            return False

        try:
            worksheet = spreadsheet.worksheet('Submissions')
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Submissions", rows=1, cols=1)

        worksheet.clear()

        title_row = [
            'Company Name',
            'Submission Link',
            'Email',
            'Company Website',
            'Sector',
            'Continent',
            'Country Code',
            'Country',
            'Region',
            'City',
            'Status',
            'Started Date',
            'Submitted Date',
        ]

        questions = set()
        for bundle in affiliate.question_bundles.prefetch_related('questions').filter(has_team_member_questions=False):
            for question in bundle.questions.all():
                questions.add(question.short_name)

        title_row.extend(list(questions))
        rows = [title_row]

        if affiliate.flow_type == Affiliate.SDG:
            submissions = SDGAffiliateProgramEntry.objects.filter(affiliate=affiliate).order_by('created_at').all()
        else:
            submissions = AffiliateProgramEntry.objects.filter(affiliate=affiliate).order_by('created_at').all()

        for submission in submissions:
            new_row = get_affiliate_submission_worksheet_row(worksheet, submission, title_row, questions)
            rows.append(new_row)

        worksheet.append_rows(rows)

        return True
    except Exception as exception:
        return False


def get_affiliate_submission_worksheet_row(sheet, submission, title_row, questions=None):
    try:
        if not questions:
            questions = [
                column
                for column in title_row
                if column
                not in [
                    'Company Name',
                    'Submission Link',
                    'Email',
                    'Company Website',
                    'Sector',
                    'Location',
                    'Continent',
                    'Country Code',
                    'Country',
                    'Region',
                    'City',
                    'Status',
                    'Started Date',
                    'Submitted Date',
                ]
            ]

        new_row = [
            submission.user_profile.company.name,
            f"https://{os.getenv('APP_BASE_URL', 'viral.vilcap.com')}/program/submission/{submission.uid}",
            submission.user_profile.user.email,
            submission.user_profile.company.website,
            ','.join(map(lambda sector: sector.name, submission.user_profile.company.sectors.all())),
        ]

        location = submission.user_profile.company.locations.first()
        if len(title_row) >= 6 and title_row[5] == 'Continent':
            new_row += [
                location.continent if location else '',
                location.country_code if location else '',
                location.country if location else '',
                location.region if location else '',
                location.city if location else '',
            ]
        else:
            new_row.append(location.formatted_address if location else '')

        new_row += [
            'Complete',
            submission.created_at.strftime('%Y/%m/%d %H:%M:%S'),
            submission.created_at.strftime('%Y/%m/%d %H:%M:%S'),
        ]

        responses = {}
        for response in submission.responses.prefetch_related('question').all():
            if response.value:
                if 'text' in response.value:
                    value = response.value['text']
                elif 'value' in response.value:
                    value = response.value['value']
                elif 'date' in response.value:
                    value = response.value['date']
                elif 'min' in response.value and 'max' in response.value:
                    value = f"[{response.value['min']}, {response.value['max']}]"
                else:
                    value = str(response.value)
            else:
                value = ' - '.join(map(lambda answer: answer.value, response.answers.all()))

            if response.question.slug == 'sdg-industry' or response.question.slug == 'sdg-activities':
                if 'options' in response.value:
                    value = ', '.join(map(lambda option: option.get('value', ''), response.value['options']))
            responses[response.question.short_name] = value

        new_row.extend(responses.get(question, '') for question in questions)
        return new_row
    except Exception as exception:
        print("Error getting affiliate submission worksheet row", exception)
        return []


def rewrite_affiliate_spreadsheet(affiliate):
    spreadsheet = get_affiliate_spreadsheet(affiliate)
    if not spreadsheet:
        return False

    if affiliate.flow_type != Affiliate.SDG:
        write_affiliate_assessments_worksheet(spreadsheet, affiliate)
    write_affiliate_submissions_worksheet(spreadsheet, affiliate)
    share_affiliate_spreadsheet(spreadsheet, affiliate)


def share_affiliate_spreadsheet(spreadsheet, affiliate):
    # Gather all email addresses the spreadsheet should be shared with
    addresses = [
        os.getenv('SPREADSHEET_EMAIL', 'vildrive@vilcap.com'),
        *(os.getenv('SPREADSHEET_SECONDARY_EMAILS', '').split(',') or []),
        affiliate.email,
        *(affiliate.additional_emails or []),
    ]

    # Filter out empty strings, remove duplicates using set
    addresses = set(filter(bool, addresses))

    # Get the list of emails the spreadsheet is already shared with
    already_shared = [permission.get('emailAddress') for permission in spreadsheet.list_permissions()]

    # Filter out the addresses that have already been shared with
    addresses = list(filter(lambda address: address not in already_shared, addresses))

    # Share the spreadsheet with the remaining addresses
    try:
        for email in addresses:
            spreadsheet.share(email, perm_type='user', role='writer')
    except APIError as exception:
        bugsnag.notify(exception)


def add_affiliate_program_entry_to_google_sheet(program_entry):
    print("Adding affiliate program entry to google sheet")
    try:
        if program_entry.affiliate.flow_target != Company.ENTREPRENEUR or (
            program_entry.affiliate.flow_type != Affiliate.PROGRAM
            and program_entry.affiliate.flow_type != Affiliate.SDG
        ):
            print("Not adding affiliate program entry to google sheet")
            return False

        spreadsheet = get_affiliate_spreadsheet(program_entry.affiliate)

        if not spreadsheet:
            return rewrite_affiliate_spreadsheet(program_entry.affiliate)

        try:
            print("Getting submissions worksheet")
            worksheet = spreadsheet.worksheet('Submissions')
        except gspread.exceptions.WorksheetNotFound:
            print("Adding submissions worksheet")
            worksheet = spreadsheet.add_worksheet(title="Submissions", rows=1, cols=1)

        title_row = worksheet.row_values(1)
        new_row = get_affiliate_submission_worksheet_row(worksheet, program_entry, title_row)
        worksheet.append_row(new_row)
    except Exception as exception:
        print("Error adding affiliate program entry to google sheet", exception)
        bugsnag.notify(exception)


def run_new_user_webhook(registration_type, user_profile):
    try:
        company = user_profile.company
        data = {}

        if company.type == Company.ENTREPRENEUR:
            sectors = company.sectors.all()
            sectors_groups = [list(sector.groups.values_list('name', flat=True).distinct()) for sector in sectors]
            unique_sector_groups = flatten(sectors_groups)
            assessment = company.latest_assessment()
            level = assessment.level.value if assessment else None
            category_levels = assessment.data if assessment else None

            data = {
                'type': registration_type,
                'company': {
                    'name': company.name,
                    'type': Company.USER_TYPE[company.type][1],
                    'email': user_profile.user.email,
                    'website': company.website,
                    'locations': company.locations.values(
                        'formatted_address',
                        'latitude',
                        'longitude',
                        'city',
                        'region',
                        'region_abbreviation',
                        'country',
                        'continent',
                    ).first(),
                    'sectors': list(map(lambda sector: sector.name, sectors)),
                    'sectors_groups': unique_sector_groups,
                    'profile': 'https://'
                    + os.getenv('APP_BASE_URL', 'my.abaca.app')
                    + '/profile/v/'
                    + company.access_hash,
                    'id': company.id,
                    'uid': company.uid,
                },
                'affiliate': {
                    'name': user_profile.source.name,
                    'id': user_profile.source.id,
                },
                'level': level,
                'category_levels': category_levels,
            }
        else:
            supporter = user_profile.supporter.first()
            locations_of_interest = list(
                location.formatted_address.capitalize() for location in supporter.locations.all()
            )
            sectors_of_interest = list(map(lambda sector: sector.name.capitalize(), supporter.sectors.all()))
            # sector groups of interest
            interest_sectors = supporter.sectors_of_interest.exclude(group=None)
            sector_groups = [interest_sector.group.name for interest_sector in interest_sectors]
            sector_unique_groups = sorted(set(sector_groups))
            data = {
                'type': registration_type,
                'supporter': {
                    'name': company.name,
                    'type': Company.USER_TYPE[company.type][1],
                    'email': user_profile.user.email,
                    'website': company.website,
                    'locations': company.locations.values(
                        'formatted_address',
                        'latitude',
                        'longitude',
                        'city',
                        'region',
                        'region_abbreviation',
                        'country',
                        'continent',
                    ).first(),
                    'profile': 'https://'
                    + os.getenv('APP_BASE_URL', 'my.abaca.app')
                    + '/profile/v/'
                    + company.access_hash,
                    'id': company.id,
                    'uid': company.uid,
                },
                'viral_range': [supporter.investing_level_range.lower, supporter.investing_level_range.upper],
                'locations_of_interest': locations_of_interest,
                'sectors_of_interest': sectors_of_interest,
                'sectors_groups_of_interest': sector_unique_groups,
            }

        # Hardcoded URL as requested by the client
        # https://pixelmatters.slack.com/archives/CAGP5U9NV/p1687424849020529
        webhook_response = requests.post('https://hook.us1.make.com/lxskmvwzancfqjlbacrhuw9nxsybikq5', json=data)
        log_data = {
            'status': webhook_response.status_code,
            'headers': webhook_response.headers,
            'request': {
                'url': webhook_response.request.url,
                'headers': webhook_response.request.headers,
                'method': webhook_response.request.method,
                'body': webhook_response.request.body,
            },
        }

        Logs.objects.create(slug='webhook', level='info' if webhook_response.ok else 'error', log=log_data)
    except Exception as exception:
        bugsnag.notify(
            Exception("Failed running new user webhook."),
            metadata={"email": user_profile.user.email, "exception": exception},
        )

