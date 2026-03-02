from django.core.management.base import BaseCommand

from grid.models.category import Category
from grid.models.level import Level
from grid.models.category_level import CategoryLevel
from grid.models.level_filter import LevelFilter
from grid.models.assessment import Assessment
from grid.models.agent_level import AgentLevel


def getAttribute(listDesc, cat, pos, attr, default):
    """
    TODO: This is just a temporary fn only for test propuses
    """
    if not cat in listDesc or len(listDesc[cat]) <= pos:
        return default

    data = listDesc[cat][pos]

    if attr in data:
        return data[attr]

    return default


class Command(BaseCommand):
    help = 'Seed Grid Database with categories, levels and category levels data'

    def handle(self, *args, **options):
        CategoryLevel.objects.all().delete()
        Level.objects.all().delete()
        Category.objects.all().delete()

        # Levels
        levels = [
            {
                'value': 1,
                'title': 'You back the Jockey, not the Horse',
                'description': 'You back strong founding teams with a solid idea.',
            },
            {
                'value': 2,
                'title': 'You back big ideas',
                'description': 'You invest in strong founding teams with a strong idea and a working prototype of their product/service that they’ve already put in front of customers.',
            },
            {
                'value': 3,
                'title': 'You back teams that have hit a value proposition',
                'description': 'You’re looking for companies that have evidence of a strong value proposition. They have validated through initial customer traction that they are solving the customer’s problem and that they are significantly and quantifiably better than their competition.',
            },
            {
                'value': 4,
                'title': 'You back teams going after big markets',
                'description': 'You typically invest in an angel round (up to $100K in investment in up to $500K of a round). You want to see that the team has as massive market ($1B+ if you’re investing equity) and has initial traction (100 customers if B2C, 5 customers if B2B).',
            },
            {
                'value': 5,
                'title': 'You back working business models',
                'description': 'You typically invest in a seed round (up to $250K in investment in up to $1M of a round). You want to see that the team has positive unit economics, even if the company isn’t yet profitable, and evidence of both revenues and costs through a couple of sales cycles.',
            },
            {
                'value': 6,
                'title': 'You back products that are rapidly scaling',
                'description': 'You typically invest in a heavy seed/light series A round ($100-$500K in investment in up to $2M of a round). You want to see that the team has a product or service that has survived a couple of sales cycles, and has initial evidence that customers are delighted by the product.',
            },
            {
                'value': 7,
                'title': 'You back teams once they’ve reached product-market fit',
                'description': 'You invest in Series A rounds and look for companies with solid positive unit economics who have more sales leads coming inbound than outbound. At this point the company’s C-Suite is filled out and is as good or better than the CEO.',
            },
            {
                'value': 8,
                'title': 'You back teams for growth/scale',
                'description': 'You come in for Series B/C and later rounds. You look for companies that are growing fast. They’re an established brand and consistently beating industry benchmarks in month-over-month revenue.',
            },
            {
                'value': 9,
                'title': 'You acquire companies',
                'description': 'You come in for Series B/C and later rounds. You look for companies that are growing fast. They’re an established brand and consistently beating industry benchmarks in month-over-month revenue.',
            },
        ]
        for level in levels:
            Level.objects.create(
                value=level['value'], title=level['title'], description=level['description'])

        # Category
        categories = [
            {
                'name': 'Team',
                'requirements_title': 'First, we’d like to know more about how your team works.',
                'color': 'ffd36f',
                'abbreviation': 'T',
            },
            {
                'name': 'Problem and Vision',
                'requirements_title': 'Let us know about the problem and vision of your company.',
                'color': 'ff8e54',
                'abbreviation': 'PV',
            },
            {
                'name': 'Value Proposition',
                'requirements_title': 'Now we’re curious about the value proposition of your company.',
                'color': 'ff5a64',
                'abbreviation': 'VP',
            },
            {
                'name': 'Product',
                'requirements_title': 'Requirements title',
                'color': '43d38a',
                'abbreviation': 'P',
            },
            {
                'name': 'Market',
                'requirements_title': 'Requirements title',
                'color': '3fc7c0',
                'abbreviation': 'M',
            },
            {
                'name': 'Business Model',
                'requirements_title': 'Requirements title',
                'color': 'f462a2',
                'abbreviation': 'BM',
            },
            {
                'name': 'Scale',
                'requirements_title': 'Requirements title',
                'color': 'a86ff5',
                'abbreviation': 'S',
            },
            {
                'name': 'Exit',
                'requirements_title': 'Finally, let us know how close is your company from exiting.',
                'color': '526def',
                'abbreviation': 'E',
            },
        ]
        for category in categories:
            Category.objects.create(name=category['name'], requirements_title=category['requirements_title'],
                                    color=category['color'], abbreviation=category['abbreviation'])

        achievements = [
            [
                'We have 2+ co-founders with different skills sets.',
                'Our team have personally experienced the problem.',
                'Our team can build the product and understands the value.',
                'We understand how our target market operates.',
                'We have a clear strategy and understanding of sales.',
                'Our team has proven sales, product development, and management skills.',
                'We have an executive team that can lead the company through growth.',
                'Our team is recognized as market leaders in the industry.',
                'Our team is prepared to navigate a merger, acquisition, or IPO.',
            ],
            [
                'We’ve identified a specific, important, and large problem.',
                'We can solve the problem and can describe our vision at scale.',
                'We’re the best ones to solve this problem and I can articulate why.',
                'We can explain how this solution will transform the industry.',
                'Growing our business will contribute to solving the problem.',
                'Our sales and growing scale validate that we’re solving the problem.',
                'We’ve begun to impact the industry.',
                'We’ve achieved systems-level change in our industry.',
                'We’re a global leader in solving this problem.',
            ],
            [
                'We have a specific target customer whose problem we are solving.',
                'Customers who validate that our solutions solves a key point.',
                'We have evidence that customers will pay our target price.',
                'Customer feedback shows that our solution is better than others.',
                'Target customers love the product and want to keep using it.',
                'We’re selling beyond our initial target customers.',
                'The majority of our sales in our initial market are inbound.',
                'Customers and renewing or repurchasing without much sales efforts.',
                'We’re recognized as the top solution solving this problem.',
            ],
            [
                'We have the ability to develop a low-fi prototype.',
                'We’ve built a low-fi prototype that solves the problem.',
                'We’ve built a working prototype and have a product roadmap.',
                'Our team understands product management.',
                'The product is almost ready for broad commercial distribution.',
                'The product is complete, in the market, and receiving user feedback.',
                'Product is built for scale and additional offerings are in progress.',
                'We’re receiving strong positive customer feedback in multiple markets.',
                'Our product is recognized as the top in the industry.',
            ],
            [
                'We know our total addressable market and target market share.',
                'We understand the landscape and have a strategy for compliance.',
                'Initial sales are evidence that we can capture our target market.',
                'We can demonstrate that our total addressable market is over $1B.',
                'Partners are talking with us about distribution, marketing, etc.',
                'Our supply and distribution partners see their success with us.',
                'Our sales cycle meets or beats the industry standard.',
                'We have partnerships for distribution, marketing, and growth.',
                'We have a clear line of sight to industry dominance.',
            ],
            [
                'An outline of a revenue model is coming together.',
                'Pricing and business models support our revenue assumptions.',
                'We know the costs in our value chain.',
                'We have projected revenues and costs.',
                'Actual revenue provide evidence we can reach positive unit economics.',
                'Customer acquisition costs are going down.',
                'Our unit economics are positive.',
                'Month-over-month revenue meets industry standard.',
                'Revenue has been doubling, or more, each year for several years.',
            ],
            [
                'We’ve identified multiple possible markets or customer segments.',
                'Initial evidence shows that multiple markets experience this problem.',
                'We have a strategy to scale to multiple markets.',
                'Multiple customers show evidence of finding value in our solution.',
                'Unit economics are tipping to positive in at least two markets.',
                'We’ve cleared regulatory challenges and have a clear IP strategy.',
                'Our unit economics are positive in multiple markets.',
                'Growth in our customer base is accelerating month-on-month',
                'Economics are positive for multiple customers and multiple markets.',
            ],
            [
                'We know what an exit is and have an idea of how to reach one.',
                'Our vision includes us solving of the problem within 10 years.',
                'Initial evidence shows we solve the problem better than incumbents.',
                'Evidence of growth trajectory that lead to IPO or other exit.',
                'We’re seeing Inbound interest from large strategic partners.',
                'We’ve identified specific acquirer(s) or other exit options.',
                'We have strong relationships with multiple potential acquirers.',
                'We’ve turned down an acquisition offer already.',
                'We’re growing fast and an exit is in sight.',
            ]
        ]

        requirements = [
            [
                'Requirements.',
                'Requirements.',
                'Requirements.',
                '- Both cofounders have worked as executives in our industry for 10+ years.\n- I can name and have personal connections with, 5 key distributors and marketers.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ],
            [
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ],
            [
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ],
            [
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ],
            [
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ],
            [
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ],
            [
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ],
            [
                'Requirements.',
                'Requirements.',
                '- Both cofounders have worked as executives in our industry for 10+ years.\n- I can name and have personal connections with, 5 key distributors and marketers.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
                'Requirements.',
            ]
        ]

        descriptions = [
            [
                'Description.',
                'Description.',
                'Description.',
                'Team has senior members with lived experience of the problem and/or deep understanding of their target customer’s problem.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ],
            [
                'Description.',
                'The company can articulate why they’re the best ones to solve this problem.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ],
            [
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Target customers love the product and want to keep using it.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ],
            [
                'Description.',
                'Description.',
                'Team has senior members with lived experience of the problem and/or deep understanding of their target customer’s problem.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ],
            [
                'Description.',
                'Description.',
                'Evidence of $1B+ total addressable market.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ],
            [
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Team can articulate projected costs along the value chain and target cost points to reach positive unit economics.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ],
            [
                'Description.',
                'Description.',
                'Clear strategy to move to multiple markets.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ],
            [
                'Description.',
                'Description.',
                'Vision for growth has company solving a large piece of the global problem in 10 years.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
                'Description.',
            ]
        ]

        for categoryIndex, category in enumerate(Category.objects.all().order_by('order'), start=0):
            # Category Levels Details
            for levelIndex, level in enumerate(Level.objects.all().order_by('value'), start=0):
                achievement = achievements[categoryIndex][levelIndex]
                requirement = requirements[categoryIndex][levelIndex]
                description = descriptions[categoryIndex][levelIndex]

                CategoryLevel.objects.create(level=level, category=category, achievements=achievement, requirements=requirement,
                                             agent_expectation_likes="(what the agent might like at this level)", agent_expectation_questions="(what the agent might ask at this level)",
                                             user_expectation_likes="(what the user might like at this level)", user_expectation_questions="(what the user might ask at this level)",
                                             description=description)

        self.stdout.write(self.style.SUCCESS(
            'Successfully seeded Grid Database with dummy data'))
