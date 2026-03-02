from mailjet_rest import Client
import os
import json
import datetime
import bugsnag
import settings
from django.core.mail import get_connection
from django.core.mail.message import EmailMessage
from viral.models import UserProfile, Company, UserMetadata
from grid.models import Assessment, CategoryLevel, Level
from shared.models import Logs


TEMPLATE = 'template.json'

AFFILIATE = '_affiliate.json'
ASSESSMENT = '_assessment.json'
COMPANY = '_company.json'

FORGOT_PASSWORD = (0, 'forgot_password.json')
VERIFY_ACCOUNT = (1, 'verify_account.json')
SUCCESS_CREATING_ACCOUNT = (2, 'success_creating_account.json')
RECOVER_USER = (3, 'recover_user.json')
NOTIFICATION_TO_AFFILIATE = (4, 'notification_to_affiliate.json')
ENTREPRENEUR_COMPLETED_ASSESSMENT = (
    5, 'entrepreneur_completed_assessment.json')
ENTREPRENEUR_COMPLETED_PROGRAM = (
    6, 'entrepreneur_completed_program.json')
WEEKLY_DIGEST = (
    7, 'weekly_digest.json')
ORGANIZATION_COMPLETED_PROGRAM = (
    8, 'organization_completed_program.json')
### ESO uses the same mailjet template (index==8) as ORGANIZATION/SMALL_FOUNDATION
ESO_COMPLETED_PROGRAM = (
    8, 'eso_completed_program.json')


def getJson(name):
    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir, './templates/' + name)
    with open(file_path) as f:
        template = json.load(f)
    return template


def getAffiliate(affiliate):
    data = getJson(AFFILIATE)
    data['name'] = affiliate.name
    data['email'] = affiliate.email
    return data


def getCompany(user):
    try:
        company = Company.objects.get(company_profile__user=user)
        assessment = Assessment.objects.filter(user=user.id).order_by("created_at").first()
    except (Company.DoesNotExist, Assessment.DoesNotExist):
        return

    data = getJson(COMPANY)
    data['name'] = company.name
    data['email'] = user.email
    data['website'] = company.website
    data['role'] = "Entrepreneur"
    company_location = company.locations.all(
    )[0].formatted_address if company.locations.exists() else ''
    data['location'] = company_location
    data['foundedDate'] = company.founded_date.strftime(
        '%d %B %Y') if company.founded_date else ''
    data['about'] = company.about

    if assessment != None:
        data['viralLevel']['title'] = assessment.level.title
        data['viralLevel']['value'] = assessment.level.value
        data['viralLevel']['description'] = assessment.level.description
    index = 0

    for sector in company.sectors.all():
        data['sectors'].append(
            {
                "index": index,
                "value": sector.name
            }
        )
        index += 1

    data['sectorsLength'] = len(data['sectors'])
    return data


def getAssessment(user, group=2):
    try:
        Company.objects.get(company_profile__user=user)
        assessment = Assessment.objects.filter(user=user.id).order_by('-created_at')[0:1].get()
        totalLevels = Level.objects.filter(group=group).count()
    except (Company.DoesNotExist, Assessment.DoesNotExist) as e:
        print(e)
        return
    data = getJson(ASSESSMENT)
    data['currentLevel'] = assessment.level.value

    category_ids = [level['category'] for level in assessment.data]
    category_levels = CategoryLevel.objects.select_related(
        'category').filter(category__in=category_ids, level=assessment.level)

    for index, level in enumerate(assessment.data, start=1):
        categoryLevel = next((category_level for category_level in category_levels
                              if level['category'] == category_level.category.pk), None)
        if not categoryLevel:
            continue

        category = categoryLevel.category
        currentLevel = level['level'] or 0
        levelDescription = categoryLevel.description if currentLevel != 0 else data[
            'emptyLevel']

        data['categories'].append(
            {
                'abbreviation': category.abbreviation,
                'color': category.color,
                'level': currentLevel
            }
        )
        data['levels'].append(
            {
                'index': index,
                'category': category.id,
                'level': currentLevel,
                'name': category.name,
                'color': category.color,
                'description': levelDescription,
            }
        )
    size = len(data['categories'])
    data['categoriesLength'] = size
    data['range']['first'] = totalLevels
    while totalLevels > 0:
        data['rows'].append(totalLevels)
        totalLevels -= 1
    return data


def getTemplate():
    current_year = datetime.datetime.now().year
    _copyright = 'Copyright &copy; ' + \
        str(current_year) + ', VilCap Inc. All Rights Reserved'
    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir, './templates/template.json')
    with open(file_path) as f:
        template = json.load(f)
    template['copyright'] = _copyright
    return template


def sendEmail(data):
    if settings.IS_RUNNING_DEVSERVER and os.environ.get('IMAP_HOST', 'False'):
        try:
            with get_connection(
                host=os.environ.get('IMAP_HOST', '0.0.0.0'), 
                port=os.environ.get('IMAP_PORT', '1025'), 
                username=os.environ.get('IMAP_USER'), 
                password=os.environ.get('IMAP_PASS'), 
                use_tls=os.environ.get('IMAP_TLS', False)
            ) as connection:
                for message in data['Messages']:
                    if message.get('Variables'):
                        body = json.dumps(message['Variables']['data'], indent=2)
                    else:
                        body = message.get('HTMLPart') or message.get('TextPart')
                    email = EmailMessage(
                        subject=message['Subject'],
                        body=body,
                        from_email=message['From']['Email'],
                        to=[recipient['Email'] for recipient in message['To']],
                        connection=connection
                    )
                    email.content_subtype = "html"
                    email.send()
        except Exception as e:
            print(e)
    else:
        api_key = os.getenv('MJ_APIKEY', 'invalid_api_key')
        api_secret = os.getenv('MJ_APISECRET', 'invalid_api_secret')
        mailjet = Client(auth=(api_key, api_secret), version='v3.1')
        result = mailjet.send.create(data=data)
        print(result.json())
        Logs.objects.create(slug='mailjet', level='info', log=data)


def sendForgotPasswordEmail(email, user, link):
    data = getJson(FORGOT_PASSWORD[1])
    data['company'] = getCompany(user)
    data['button']['link'] = link
    sendEmailForTemplate(FORGOT_PASSWORD[0], email, data)


def sendVerifyAccountEmail(email, user, link):
    data = getJson(VERIFY_ACCOUNT[1])
    data['company'] = getCompany(user)
    data['button']['link'] = link

    # Use the new email address
    data['company']['email'] = email
    sendEmailForTemplate(VERIFY_ACCOUNT[0], email, data)


def sendSuccessCreatingAccount(email, user):
    data = getJson(SUCCESS_CREATING_ACCOUNT[1])
    data['company'] = getCompany(user)
    data['button']['link'] = 'https://' + \
        os.getenv('APP_BASE_URL', 'viral.vilcap.com') + '/auth/login'
    sendEmailForTemplate(SUCCESS_CREATING_ACCOUNT[0], email, data)


def sendRecoverUser(email, user, link):
    data = getJson(RECOVER_USER[1])
    data['company'] = getCompany(user)
    data['assessment'] = getAssessment(user)
    data['button']['join']['link'] = link
    data['button']['sign']['link'] = link
    sendEmailForTemplate(RECOVER_USER[0], email, data)


def sendNotificationToAffiliate(email, user, affiliate, link):
    data = getJson(NOTIFICATION_TO_AFFILIATE[1])
    data['affiliate'] = getAffiliate(affiliate)
    data['company'] = getCompany(user)
    data['assessment'] = getAssessment(user)
    data['subject'] = 'New Company Assessment: ' + data['company']['name'] + \
        ' - Level ' + str(data['assessment']['currentLevel'])
    data['content']['message'] = '<b>' + data['company']['name'] + \
        '</b> just completed their Venture Investments Level self-assessment, and are a <b>Level ' + \
        str(data['assessment']['currentLevel']) + '</b> company!'
    data['content']['modules']['assessment']['button']['link'] = link
    data['button']['link'] = link
    sendEmailForTemplate(NOTIFICATION_TO_AFFILIATE[0], email, data)
    if affiliate.additional_emails:
        for email in affiliate.additional_emails:
            sendEmailForTemplate(NOTIFICATION_TO_AFFILIATE[0], email, data)


def sendEntrepreneurCompletedAssessment(email, user, link, group):
    data = getJson(ENTREPRENEUR_COMPLETED_ASSESSMENT[1])
    data['company'] = getCompany(user)
    data['assessment'] = getAssessment(user)
    try:
        levels = Level.objects.filter(group=group)
        level = levels.get(value=data['assessment']['currentLevel'])
    except Level.DoesNotExist:
        return
    data['subject'] = 'Your Venture Investment Level ' + \
        str(data['assessment']['currentLevel']) + ' - ' + level.title
    data['content']['message'] = 'Congrats <b>' + data['company']['name'] + \
        '</b>! Your assessment was submitted successfully.<br> You are a <b>Level ' + \
        str(data['assessment']['currentLevel']) + '</b> company!'
    data['content']['modules']['assessment']['button']['link'] = link
    data['button']['link'] = link
    sendEmailForTemplate(ENTREPRENEUR_COMPLETED_ASSESSMENT[0], email, data)


def sendEntrepreneurCompletedProgram(email, user, affiliate, submissionLink, logInLink):
    data = getJson(ENTREPRENEUR_COMPLETED_PROGRAM[1])
    data['subject'] = 'Thanks for Submitting'
    data['company'] = getCompany(user)
    data['affiliate'] = getAffiliate(affiliate)
    data['content']['message'] = data['content']['message'].format(
        company_name=data['company']['name'], affiliate_name=data['affiliate']['name'])
    data['assessment'] = getAssessment(user)
    data['button']['join']['link'] = logInLink
    data['button']['submission']['link'] = submissionLink
    sendEmailForTemplate(ENTREPRENEUR_COMPLETED_PROGRAM[0], email, data)


def sendOrganizationCompletedProgram(email, user, affiliate):
    data = getJson(ORGANIZATION_COMPLETED_PROGRAM[1])
    data['subject'] = 'Thanks for Submitting'
    data['company'] = getCompany(user)
    data['affiliate'] = getAffiliate(affiliate)
    data['content']['message'] = data['content']['message'].format(
        company_name=data['company']['name'], affiliate_name=data['affiliate']['name'])
    sendEmailForTemplate(ORGANIZATION_COMPLETED_PROGRAM[0], email, data)


def sendESOCompletedProgram(email, user, affiliate):
    data = getJson(ESO_COMPLETED_PROGRAM[1])
    data['company'] = getCompany(user)
    data['affiliate'] = getAffiliate(affiliate)
    data['content']['message'] = data['content']['message'].format(
        company_name=data['company']['name'], affiliate_name=data['affiliate']['name'])
    sendEmailForTemplate(ESO_COMPLETED_PROGRAM[0], email, data)
    

def sendViralLevelRange(email, viralRange):
    data = {}
    data['subject'] = 'Viral Level Range'
    data['message'] = 'The range of levels to support: ' + viralRange
    sendEmailWithoutTemplate(email, data)


def sendWeeklyDigest(email, uid, matching_suggestions=None, requests_received=None, new_connections=None):
    data = getJson(WEEKLY_DIGEST[1])
    data['company_uid'] = uid
    data['company_email'] = email

    base_url = 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app')

    # TODO: Refactor for populating each list dynamically
    if matching_suggestions:
        showcase = data['content']['showcase']['matching_suggestions']
        title_key = 'title_singular' if len(
            matching_suggestions) == 1 else 'title_multiple'
        showcase['title'] = showcase[title_key].format(
            len(matching_suggestions))
        showcase['cta']['link'] = base_url + '/matching'
        showcase['items'] = matching_suggestions
        showcase['has_items'] = True

    if requests_received:
        showcase = data['content']['showcase']['requests_received']
        title_key = 'title_singular' if len(
            requests_received) == 1 else 'title_multiple'
        showcase['title'] = showcase[title_key].format(
            len(requests_received))
        # todo: link for requests received
        showcase['cta']['link'] = base_url + '/matching'
        showcase['items'] = requests_received
        showcase['has_items'] = True

    if new_connections:
        showcase = data['content']['showcase']['new_connections']
        title_key = 'title_singular' if len(
            new_connections) == 1 else 'title_multiple'
        showcase['title'] = showcase[title_key].format(
            len(new_connections))
        showcase['cta']['link'] = base_url + '/matching'
        showcase['items'] = new_connections
        showcase['has_items'] = True

    # TODO: Add callout logic once we have commercialization
    # data['callout'] = ...

    campaign = {
        'campaign_name': 'Weekly Digest',
        'campaign_deduplicate': False
    }
    sendEmailForTemplate(WEEKLY_DIGEST[0], email, data, **campaign)


def sendEmailForTemplate(pos, email, data, **kwargs):
    templateId = int(os.getenv('EMAIL_TEMPLATES').split(',')[pos])
    from_email = os.getenv('NO_REPLY_EMAIL', 'noreply@vilcap.com')
    template = getTemplate()
    campaign = kwargs.get('campaign_name', None)
    avoid_repeated_campaigns = kwargs.get('campaign_deduplicate', True)

    data = {
        'Messages': [
            {
                "From": {
                    "Email": from_email,
                    "Name": "Abaca"
                },
                "To": [
                    {
                        "Email": email,
                    }
                ],
                "Subject": data['subject'],
                "TemplateID": templateId,
                "TemplateLanguage": True,
                "TemplateErrorReporting": {
                    "Email": "abaca-dev@wearepixelmatters.com",
                    "Name": "Pixelmatters"
                },
                "Variables": {
                    "template": template,
                    "data": data,
                }
            }
        ]
    }

    if campaign:
        data['CustomCampaign'] = campaign
        data['DeduplicateCampaign'] = avoid_repeated_campaigns

    sendEmail(data)


def sendEmailWithoutTemplate(email, data):
    from_email = os.getenv('NO_REPLY_EMAIL', 'abaca-dev@wearepixelmatters.com')
    author = data['author'] if 'author' in data else None

    data = {
        'Messages': [
            {
                "From": {
                    "Email": from_email,
                    "Name": "Abaca"
                },
                "To": [
                    {
                        "Email": email,
                    }
                ],
                "Subject": data['subject'],
                "TextPart": data['message'],
                "HTMLPart": data['message']
            }
        ]
    }

    if author:
        data['Messages'][0]['TextPart'] += "Email: " + author
        data['Messages'][0]['HTMLPart'] += "<br> Email: " + author

    sendEmail(data)


def requestContactExclusion(email):
    """
    Since we're using the Mailjet Send API to
    send a template as a campaign we'll need also
    to store exclusions on our API and manage 
    which users will receive campaigns
    """
    api_key = os.getenv('MJ_APIKEY', 'invalid_api_key')
    api_secret = os.getenv('MJ_APISECRET', 'invalid_api_secret')
    mailjet = Client(auth=(api_key, api_secret))
    data = {
        'IsExcludedFromCampaigns': 'true'
    }
    try:
        user_profile = UserProfile.objects.get(user__email=email)
        user_meta = UserMetadata.objects.get_or_create(
            key='mailjet.exclusion', value='true', user_profile=user_profile)
        return mailjet.contact.update(id=email, data=data)
    except:
        bugsnag.notify(Exception("Mailjet: could not find user profile."),
                       meta_data={'context': {'email': email}})
        return False
